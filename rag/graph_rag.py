# rag/graph_rag.py
from langchain_community.vectorstores import Milvus
from langchain_openai import OpenAIEmbeddings
from langchain_core.retrievers import BaseRetriever
from langchain.schema import Document
from typing import List, Dict, Any
import neo4j

class GraphRAG:
    """
    GraphRAG implementation that combines vector similarity search with
    graph-based retrieval for enhanced context.
    """
    
    def __init__(self, milvus_host, milvus_port, collection_name, 
                 neo4j_uri, neo4j_user, neo4j_password, 
                 embedding_model=None):
        """Initialize GraphRAG with Milvus and Neo4j connections"""
        # Initialize embedding model
        self.embeddings = embedding_model or OpenAIEmbeddings()
        self.retriever = BaseRetriever()
        
        # Initialize Milvus vector store
        self.vector_store = Milvus(
            embedding_function=self.embeddings,
            collection_name=collection_name,
            connection_args={"host": milvus_host, "port": milvus_port}
        )
        
        # Initialize Neo4j connection
        self.driver = neo4j.GraphDatabase.driver(
            neo4j_uri, auth=(neo4j_user, neo4j_password)
        )
    
    def add_documents(self, documents: List[Document]):
        """Add documents to both vector store and knowledge graph"""
        # Add to vector store
        self.vector_store.add_documents(documents)
        
        # Extract entities and relationships for knowledge graph
        # This would typically be handled by the KG Agent
        return f"Added {len(documents)} documents to vector store"
    
    def vector_search(self, query: str, k: int = 5):
        """Perform vector similarity search"""
        return self.vector_store.similarity_search(query, k=k, retriever=self.retriever)
    
    def graph_search(self, entity_type: str, properties: Dict[str, Any], depth: int = 2):
        """Perform graph-based search starting from an entity"""
        with self.driver.session() as session:
            # Build match clause for the starting entity
            props_str = " AND ".join([f"e.{k} = ${k}" for k in properties.keys()])
            
            # Query to find connected entities up to specified depth
            query = f"""
            MATCH path = (e:{entity_type})-[*1..{depth}]-(connected)
            WHERE {props_str}
            RETURN path
            """
            
            result = session.run(query, **properties)
            return [dict(record) for record in result]
    
    def hybrid_search(self, query: str, k_vector: int = 3, graph_depth: int = 2):
        """
        Perform hybrid search combining vector similarity and graph traversal
        1. Find relevant documents via vector search
        2. Extract entities from those documents
        3. Use graph traversal to find related entities
        4. Combine and rank results
        """
        # Step 1: Vector similarity search
        vector_results = self.vector_search(query, k=k_vector)
        
        # Step 2: Extract entities from vector results
        entities = []
        for doc in vector_results:
            if 'task_id' in doc.metadata:
                entities.append({
                    'type': 'Task',
                    'properties': {'task_id': doc.metadata['task_id']}
                })
        
        # Step 3: Graph traversal for each entity
        graph_results = []
        for entity in entities:
            graph_results.extend(
                self.graph_search(
                    entity['type'], 
                    entity['properties'],
                    depth=graph_depth
                )
            )
        
        # Step 4: Combine and rank results
        # For simplicity, we'll just return both sets of results
        return {
            'vector_results': vector_results,
            'graph_results': graph_results
        }
    
    def close(self):
        """Close connections"""
        self.driver.close()