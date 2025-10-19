import logging
import pathlib
import re
import shutil
import subprocess
import tempfile
from typing import Iterable, List

from src.app.core.config import settings

logger = logging.getLogger(__name__)


class OntologySanitizer:
    """
    Pluggable sanitation pipeline that prepares ontology files for downstream parsing.

    Each sanitizer step receives the current working file path and returns a new path
    (which may be the same file) for subsequent steps. The original input is copied
    into a temporary directory to keep transformations isolated.
    """

    def __init__(self, *, workspace: pathlib.Path | None = None):
        self.workspace = workspace or pathlib.Path(tempfile.mkdtemp(prefix="ontology-sanitize-"))
        self.steps: List[SanitizerStep] = []
        self._install_default_steps()

    def _install_default_steps(self):
        self.steps.append(RobotSanitizerStep())
        self.steps.append(LiteralTruncationStep())
        self.steps.append(LanguageTagFixStep())

    def add_step(self, step: "SanitizerStep"):
        self.steps.append(step)

    def sanitize(self, source_path: pathlib.Path) -> List[pathlib.Path]:
        """
        Run the sanitation pipeline and return a list of candidate file paths in order of preference.
        """
        working_path = self._copy_to_workspace(source_path)
        candidates = [working_path]

        for step in self.steps:
            new_candidates = []
            for candidate in candidates:
                try:
                    processed = list(step.process(candidate))
                    new_candidates.extend(processed)
                except SkipSanitizer:
                    new_candidates.append(candidate)
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.error("Sanitizer %s failed on %s: %s", step.name, candidate, exc, exc_info=True)
                    new_candidates.append(candidate)
            candidates = new_candidates

        # Ensure uniqueness while preserving order
        seen = set()
        unique_candidates = []
        for candidate in candidates:
            if candidate not in seen:
                seen.add(candidate)
                unique_candidates.append(candidate)
        return unique_candidates

    def cleanup(self):
        """Remove the workspace directory."""
        try:
            if self.workspace.exists():
                shutil.rmtree(self.workspace)
        except Exception:  # pragma: no cover
            logger.warning("Failed to clean up sanitizer workspace %s", self.workspace, exc_info=True)

    def _copy_to_workspace(self, source_path: pathlib.Path) -> pathlib.Path:
        target = self.workspace / source_path.name
        target.write_bytes(source_path.read_bytes())
        return target


class SkipSanitizer(Exception):
    """Raised by a sanitizer step to signal that it should be skipped."""


class SanitizerStep:
    """Base class for all sanitizer steps."""

    name: str = "base"

    def process(self, path: pathlib.Path) -> Iterable[pathlib.Path]:  # pragma: no cover - interface only
        raise NotImplementedError


class RobotSanitizerStep(SanitizerStep):
    """Use ROBOT (if enabled) to convert/repair ontologies and evaluate simple queries."""

    name = "robot"

    def process(self, path: pathlib.Path) -> Iterable[pathlib.Path]:
        if not settings.ROBOT_ENABLED:
            raise SkipSanitizer()

        robot_jar = settings.ROBOT_JAR_PATH
        if not robot_jar:
            logger.warning("ROBOT_ENABLED=true but ROBOT_JAR_PATH is not set; skipping ROBOT step.")
            raise SkipSanitizer()

        if not pathlib.Path(robot_jar).exists():
            logger.warning("ROBOT jar not found at %s; skipping ROBOT step.", robot_jar)
            raise SkipSanitizer()

        converted_ttl = path.with_suffix(path.suffix + ".robot.ttl")
        repaired_ttl = converted_ttl.with_suffix(".repaired.ttl")
        rdfxml_path = path.with_suffix(path.suffix + ".robot.rdf")

        generated: List[pathlib.Path] = []

        try:
            try:
                self._run_robot(["convert", "--input", str(path), "--output", str(converted_ttl)])
                if converted_ttl.exists():
                    generated.append(converted_ttl)
            except subprocess.CalledProcessError as exc:
                self._log_robot_failure("convert", path, exc)

            if converted_ttl.exists():
                try:
                    self._run_robot(["repair", "--input", str(converted_ttl), "--output", str(repaired_ttl)])
                    if repaired_ttl.exists():
                        generated.insert(0, repaired_ttl)
                except subprocess.CalledProcessError as exc:
                    self._log_robot_failure("repair", path, exc)

            try:
                self._run_robot(["convert", "--input", str(path), "--format", "rdfxml", "--output", str(rdfxml_path)])
                if rdfxml_path.exists():
                    generated.insert(0, rdfxml_path)
            except subprocess.CalledProcessError as exc:
                self._log_robot_failure("convert-rdfxml", path, exc)

            if generated:
                generated.append(path)
                logger.info("ROBOT produced %d candidate(s) for %s", len(generated), path.name)
                return generated

            raise SkipSanitizer()
        except FileNotFoundError:
            logger.warning("Java runtime not available in worker; skipping ROBOT step.")
            raise SkipSanitizer()
        except Exception as exc:  # pragma: no cover
            logger.error("Unexpected error during ROBOT preprocessing: %s", exc, exc_info=True)
            raise SkipSanitizer()

    @staticmethod
    def _run_robot(args: List[str]):
        cmd = ["java", "-jar", settings.ROBOT_JAR_PATH] + args
        return subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    @staticmethod
    def _log_robot_failure(stage: str, path: pathlib.Path, exc: subprocess.CalledProcessError):
        stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
        logger.warning("ROBOT %s failed for %s: %s", stage, path.name, stderr)


class LiteralTruncationStep(SanitizerStep):
    """Truncate excessively long literals in TTL files."""

    name = "literal-truncation"
    MAX_LITERAL_CHARS = 5000

    def process(self, path: pathlib.Path) -> Iterable[pathlib.Path]:
        suffixes = [s.lower() for s in path.suffixes]
        if ".ttl" not in suffixes:
            raise SkipSanitizer()

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")

        original_text = text

        triple_double = re.compile(r'"""(.*?)"""', re.DOTALL)
        triple_single = re.compile(r"'''(.*?)'''", re.DOTALL)
        double_quote = re.compile(r'"([^"\r\n]{%d,})"' % self.MAX_LITERAL_CHARS, re.DOTALL)
        placeholder = "[literal trimmed for sanitation]"

        def replace_block(pattern, quote):
            nonlocal text

            def replacer(match):
                content = match.group(1)
                if len(content) > self.MAX_LITERAL_CHARS:
                    return f"{quote}{placeholder}{quote}"
                return match.group(0)

            text = pattern.sub(replacer, text)

        replace_block(triple_double, '"""')
        replace_block(triple_single, "'''")

        def replace_double(match):
            content = match.group(1)
            if len(content) > self.MAX_LITERAL_CHARS:
                return f"\"{placeholder}\""
            return match.group(0)

        text = double_quote.sub(replace_double, text)

        if text == original_text:
            raise SkipSanitizer()

        truncated_path = path.with_name(path.name + ".literal")
        truncated_path.write_text(text, encoding="utf-8")
        logger.info("Literal truncation applied to %s -> %s", path.name, truncated_path.name)
        return [truncated_path, path]


class LanguageTagFixStep(SanitizerStep):
    """Remove invalid language tags from Turtle literals."""

    name = "language-tag-fix"
    VALID_TAG = re.compile(r"^[a-zA-Z]{1,8}(?:-[a-zA-Z0-9]{1,8})*$")
    LITERAL_WITH_LANG = re.compile(r'("([^"\\]|\\.)*")@([^\s"<>;]+)')

    def process(self, path: pathlib.Path) -> Iterable[pathlib.Path]:
        suffixes = [s.lower() for s in path.suffixes]
        if ".ttl" not in suffixes:
            raise SkipSanitizer()

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")

        original_text = text

        def replacer(match):
            literal, tag = match.group(1), match.group(3)
            if self.VALID_TAG.fullmatch(tag):
                return match.group(0)
            logger.debug("Removing invalid language tag '%s' from literal in %s", tag, path.name)
            return literal

        text = self.LITERAL_WITH_LANG.sub(replacer, text)

        if text == original_text:
            raise SkipSanitizer()

        fixed_path = path.with_name(path.name + ".langfix")
        fixed_path.write_text(text, encoding="utf-8")
        logger.info("Removed invalid language tags in %s -> %s", path.name, fixed_path.name)
        return [fixed_path, path]
