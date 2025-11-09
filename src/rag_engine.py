import os
import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional

class RAGEngine:
    """
    Motor RAG para Lisabella - Recupera información de libros médicos con referencias verificables
    """
    
    def __init__(self, persist_directory="./data/vectordb"):
        """Inicializar RAG engine con ChromaDB y modelo de embeddings"""
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # Modelo de embeddings (local, gratuito)
        print("🔄 Cargando modelo de embeddings...")
        self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # Cliente ChromaDB
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Colección para documentos médicos
        try:
            self.collection = self.client.get_collection("medical_books")
            print(f"✅ Colección existente cargada: {self.collection.count()} documentos")
        except:
            self.collection = self.client.create_collection(
                name="medical_books",
                metadata={"description": "Libros médicos con referencias verificables"}
            )
            print("✅ Nueva colección creada")
    
    def add_document(self, text: str, metadata: Dict):
        """
        Añadir documento a la base de datos vectorial
        
        Args:
            text: Contenido del documento
            metadata: {
                'source': 'Gray\'s Anatomy 42nd Ed.',
                'page': '1234',
                'chapter': 'Abdomen',
                'topic': 'Bazo - Ligamentos'
            }
        """
        # Generar embedding
        embedding = self.embedding_model.encode(text).tolist()
        
        # Generar ID único
        doc_id = f"{metadata.get('source', 'unknown')}_{metadata.get('page', '0')}_{metadata.get('topic', 'topic')}"
        
        # Añadir a ChromaDB
        self.collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
            ids=[doc_id]
        )
        
        print(f"✅ Documento añadido: {metadata.get('topic', 'Sin título')} - {metadata.get('source')}")
    
    def search(self, query: str, n_results: int = 3) -> List[Dict]:
        """
        Buscar documentos relevantes para una consulta
        
        Args:
            query: Pregunta del usuario
            n_results: Número de resultados a devolver
            
        Returns:
            Lista de documentos con metadata
        """
        if self.collection.count() == 0:
            return []
        
        # Generar embedding de la query
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # Buscar documentos similares
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, self.collection.count())
        )
        
        # Formatear resultados
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    'content': doc,
                    'source': results['metadatas'][0][i].get('source', 'Desconocido'),
                    'page': results['metadatas'][0][i].get('page', 'N/A'),
                    'chapter': results['metadatas'][0][i].get('chapter', 'N/A'),
                    'topic': results['metadatas'][0][i].get('topic', 'N/A'),
                    'relevance': 1 - results['distances'][0][i]  # Convertir distancia a similitud
                })
        
        return formatted_results
    
    def get_context_for_query(self, query: str, min_relevance: float = 0.7) -> Optional[str]:
        """
        Obtener contexto relevante para una consulta con referencias
        
        Returns:
            String formateado con contexto y referencias, o None si no hay resultados relevantes
        """
        results = self.search(query, n_results=3)
        
        if not results:
            return None
        
        # Filtrar por relevancia mínima
        relevant_results = [r for r in results if r['relevance'] >= min_relevance]
        
        if not relevant_results:
            return None
        
        # Formatear contexto
        context = "**CONTEXTO DE FUENTES VERIFICABLES:**\n\n"
        
        for i, result in enumerate(relevant_results, 1):
            context += f"**Fuente {i}**: {result['source']}, p.{result['page']}\n"
            context += f"{result['content']}\n\n"
        
        return context
    
    def get_stats(self) -> Dict:
        """Obtener estadísticas de la base de datos"""
        return {
            "total_documents": self.collection.count(),
            "collection_name": self.collection.name
        }
