import logging
import weaviate
import cohere
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from src.app.core.config import settings
from src.app.schemas.models import QueryResponse, SourceChunk

logger = logging.getLogger(__name__)

class RetrievalService:
    def __init__(self):
        try:
            self.weaviate_client = weaviate.Client(settings.WEAVIATE_URL)
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {e}", exc_info=True)
            raise

        self.cohere_client = None
        try:
            cohere_kwargs = {"api_key": settings.COHERE_API_KEY}
            base_url = getattr(settings, "COHERE_BASE_URL", None)
            if base_url:
                cohere_kwargs["base_url"] = base_url
            # Dummy keys will raise errors; catch and fall back gracefully.
            self.cohere_client = cohere.Client(**cohere_kwargs)
        except Exception as e:
            logger.warning("Cohere client unavailable, using lexical ranking only. Error: %s", e)
            self.cohere_client = None

        self.llm_chain = None
        try:
            llm_api_key = getattr(settings, "OPENAI_LLM_API_KEY", None) or settings.OPENAI_API_KEY
            llm_kwargs = {
                "openai_api_key": llm_api_key,
                "model_name": settings.DEFAULT_LLM_MODEL,
                "temperature": 0
            }
            llm_base_url = getattr(settings, "OPENAI_LLM_BASE_URL", None) or getattr(settings, "OPENAI_BASE_URL", None)
            if llm_base_url:
                llm_kwargs["openai_api_base"] = llm_base_url

            llm = ChatOpenAI(**llm_kwargs)
            self.prompt_template = self._create_prompt_template()
            self.llm_chain = LLMChain(prompt=self.prompt_template, llm=llm)
        except Exception as e:
            logger.warning("OpenAI client unavailable, falling back to simple answer synthesis. Error: %s", e)
            self.llm_chain = None

    @staticmethod
    def _create_prompt_template():
        template = """
        You are an expert assistant for answering questions about ontologies.
        Your answer must be based *only* on the context provided.
        If the context does not contain the information needed to answer the question, state that you cannot answer.
        Do not make up information. Be concise and accurate.

        CONTEXT:
        ---
        {context}
        ---

        QUESTION: {question}

        ANSWER:
        """
        return PromptTemplate(template=template, input_variables=["context", "question"])

    def answer_query(self, query: str) -> QueryResponse:
        """
        Executes the full retrieval-augmented generation pipeline for a given query.
        """
        # 1. Hybrid Search
        logger.info(f"Performing hybrid search for query: '{query}'")
        search_results = self._hybrid_search(query)
        if not search_results:
            return QueryResponse(answer="I could not find any relevant information in the indexed ontologies to answer your question.", sources=[])

        # 2. Re-ranking
        logger.info(f"Re-ranking {len(search_results)} search results.")
        reranked_results = self._rerank(query, search_results)
        top_k = 5
        top_results = reranked_results[:top_k]

        # 3. Prompting and Generation
        logger.info(f"Generating answer using top {len(top_results)} re-ranked results.")
        answer = self._generate_answer(query, top_results)

        # 4. Assemble Response
        source_chunks = [
            SourceChunk(
                ontology_id=res['ontology_id'],
                version=res['version'],
                content=res['content'],
                metadata=res.get('metadata', {})
            ) for res in top_results
        ]

        return QueryResponse(answer=answer, sources=source_chunks)

    def _hybrid_search(self, query: str, limit: int = 25) -> list[dict]:
        """Performs a hybrid search in Weaviate."""
        try:
            response = self.weaviate_client.query.get(
                settings.WEAVIATE_CLASS_NAME,
                ["content", "ontology_id", "version"]
            ).with_bm25(
                query=query
            ).with_limit(limit).do()
        except Exception as e:
            logger.error("Hybrid search failed: %s", e, exc_info=True)
            return []

        data_section = response.get('data', {}).get('Get', {})
        if not data_section:
            logger.warning("Weaviate search returned no data: %s", response)
            return []
        return data_section.get(settings.WEAVIATE_CLASS_NAME, [])

    def _rerank(self, query: str, documents: list[dict]) -> list[dict]:
        """Re-ranks documents using Cohere."""
        if not self.cohere_client:
            return documents

        try:
            docs_for_reranking = [doc['content'] for doc in documents]
            rerank_response = self.cohere_client.rerank(
                model=settings.DEFAULT_RERANKING_MODEL,
                query=query,
                documents=docs_for_reranking,
                return_documents=True
            )
            reranked_docs = []
            for result in rerank_response.results:
                original_doc = documents[result.index]
                reranked_docs.append(original_doc)
            return reranked_docs
        except Exception as e:
            logger.warning("Cohere rerank failed, using original ordering. Error: %s", e)
            return documents

    def _generate_answer(self, query: str, top_results: list[dict]) -> str:
        if not top_results:
            return "I could not find any relevant information in the indexed ontologies to answer your question."

        context_str = "\n\n---\n\n".join([res['content'] for res in top_results])

        if self.llm_chain:
            try:
                llm_response = self.llm_chain.invoke({
                    "context": context_str,
                    "question": query
                })
                return llm_response['text'].strip()
            except Exception as e:
                logger.warning("LLM generation failed, using fallback response. Error: %s", e)

        # Fallback: return concatenated context with prompt reminder.
        return (
            "Based on the available ontology context, here is the most relevant information:\n\n"
            f"{context_str}\n\n"
            "This answer is generated without an LLM due to missing credentials."
        )
