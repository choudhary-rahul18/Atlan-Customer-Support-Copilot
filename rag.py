import pandas as pd
from typing import Optional
import logging
import os, pickle
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi

class ExcelRAG:

    def __init__(self,chunk_file="files/chunks.json", embedding_file="files/embeddings.npy",bm25_file="files/bm25_index.pkl") -> None:
        self.df: Optional[pd.DataFrame] = None
        self.chunks: list[str] = []
        self.chunk_file = chunk_file
        self.logger = logging.getLogger(__name__)

        self.embeddings = None
        self.embedding_file = embedding_file
        self.model = SentenceTransformer('all-mpnet-base-v2')

        self.faiss_index = None
        self.faiss_index_file = "files/faiss_index.bin" 

        self.bm25_file = bm25_file
        self.bm25 = None


    def load_excel(self, file_path: str, sheet_name: Optional[str] = None) -> None:
        raw = pd.read_excel(file_path, sheet_name=sheet_name)

        if isinstance(raw, dict):                       # multiple sheets loaded
            if sheet_name is None:
                self.df = raw[next(iter(raw))]          # first sheet
            else:
                self.df = raw.get(sheet_name)
                if self.df is None:
                    raise ValueError(
                        f"Sheet '{sheet_name}' not found in '{file_path}'."
                    )
        else:
            self.df = raw                               # already a DataFrame

        self.logger.info(
            "Loaded DataFrame: %s rows × %s columns",
            len(self.df),
            len(self.df.columns),
        )
        return self.df


    # ── 2. Convert rows ➜ chunks (Data column only) ────────────────
    def load_chunks(self) -> None:
        if os.path.exists(self.chunk_file):
            with open(self.chunk_file, "r", encoding="utf-8") as f:
                self.chunks = json.load(f)
            self.logger.info(f"Loaded {len(self.chunks)} chunks from {self.chunk_file}")
            return self.chunks

        # 2. Otherwise, create chunks from Excel
        if self.df is None:
            raise ValueError("Call load_excel() before rows_to_chunks().")

        if "Data" not in self.df.columns:
            raise KeyError("'Data' column not found in the worksheet.")

        self.chunks.clear()
        for val in self.df["Data"]:
            if pd.notna(val) and str(val).strip():
                self.chunks.append(str(val))

        # Save chunks to file for reuse
        with open(self.chunk_file, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Converted {len(self.chunks)} rows into chunks and saved to {self.chunk_file}")
        return self.chunks
    
    def create_embeddings(self):
        """Create embeddings and cache them to disk"""
        try:
        # 1. Check if embeddings already exist
            if os.path.exists(self.embedding_file):
                try:
                    self.embeddings = np.load(self.embedding_file, allow_pickle=False)
                    self.logger.info(
                        "Loaded %s embeddings from cache", self.embeddings.shape[0]
                    )
                    # Build/rebuild FAISS index after loading embeddings
                    self._build_faiss_index()  # This will overwrite any existing index
                    return self.embeddings
                except (IOError, ValueError) as e:
                    self.logger.warning(
                        "Failed to load cached embeddings: %s. Recreating...", e
                    )
            
            # 2. Ensure we have chunks to embed
            if not self.chunks:
                raise ValueError("No chunks available. Call load_chunks() first.")

            if not hasattr(self, "model"):
                raise AttributeError("No model found. Set self.model before calling create_embeddings().")
            
            # 3. Create embeddings
            self.logger.info("Creating embeddings for %s chunks...", len(self.chunks))
            self.embeddings = self.model.encode(
                self.chunks, 
                show_progress_bar=True,
                convert_to_numpy=True,
                batch_size=32  # helps memory management
            )
            
            # 4. Save to disk for next time
            try:
                os.makedirs(os.path.dirname(self.embedding_file), exist_ok=True)
                np.save(self.embedding_file, self.embeddings)
                self.logger.info("Saved %s embeddings to %s", len(self.embeddings), self.embedding_file)
            except IOError as e:
                self.logger.error("Failed to save embeddings: %s", e)
            
            # 5. Build FAISS index
            self._build_faiss_index()
            
            return self.embeddings

        except Exception as e:
            self.logger.error("Failed to create embeddings: %s", e)
            raise

    def _build_faiss_index(self):
        """Build and save FAISS index for fast similarity search"""
        if self.embeddings is None:
            raise ValueError("No embeddings available. Run create_embeddings() first.")
        
        if len(self.chunks) != len(self.embeddings):
            self.logger.warning("Chunk count (%d) doesn't match embedding count (%d). "
                            "This may indicate stale data.", len(self.chunks), len(self.embeddings))
        
        self.logger.info("Building FAISS index for %d embeddings...", len(self.embeddings))
        
        try:
            # Normalize embeddings for cosine similarity
            embeddings_normalized = self.embeddings.astype(np.float32)
            faiss.normalize_L2(embeddings_normalized)
            
            # Create FAISS index
            dimension = self.embeddings.shape[1]
            self.faiss_index = faiss.IndexFlatIP(dimension)
            self.faiss_index.add(embeddings_normalized)
            
            # Verify the index was built correctly
            if self.faiss_index.ntotal != len(self.embeddings):
                raise RuntimeError(f"FAISS index count ({self.faiss_index.ntotal}) "
                                f"doesn't match embedding count ({len(self.embeddings)})")
            
            # Save index to disk (overwrite any existing)
            os.makedirs(os.path.dirname(self.faiss_index_file), exist_ok=True)
            faiss.write_index(self.faiss_index, self.faiss_index_file)
            self.logger.info("Saved FAISS index for %d vectors to %s", 
                            self.faiss_index.ntotal, self.faiss_index_file)
            
        except Exception as e:
            self.logger.error("Failed to build FAISS index: %s", e)
            # Clean up failed index
            self.faiss_index = None
            if os.path.exists(self.faiss_index_file):
                os.remove(self.faiss_index_file)
            raise

    def _load_faiss_index(self):
        """Load FAISS index from disk"""
        if os.path.exists(self.faiss_index_file):
            try:
                self.faiss_index = faiss.read_index(self.faiss_index_file)
                self.logger.info("FAISS index loaded from disk")
                return True
            except Exception as e:
                self.logger.warning("Failed to load FAISS index: %s", e)
        return False
    

    def build_bm25_index(self):
        """
        Build and cache BM25 index for keyword-based retrieval
        """
        try:
            # 1. Check if BM25 index already exists
            if os.path.exists(self.bm25_file):
                try:
                    with open(self.bm25_file, 'rb') as f:
                        self.bm25 = pickle.load(f)
                    self.logger.info("Loaded BM25 index from cache: %s", self.bm25_file)
                    return
                except Exception as e:
                    self.logger.warning("Failed to load BM25 cache: %s. Rebuilding...", e)

            # 2. Ensure we have chunks
            if not self.chunks:
                raise ValueError("No chunks available. Call load_chunks() first.")

            # 3. Tokenize chunks for BM25
            self.logger.info("Building BM25 index for %d chunks...", len(self.chunks))
            tokenized_chunks = [chunk.lower().split() for chunk in self.chunks]
            
            # 4. Build BM25 index
            self.bm25 = BM25Okapi(tokenized_chunks)

            # 5. Save to cache
            os.makedirs(os.path.dirname(self.bm25_file), exist_ok=True)
            with open(self.bm25_file, 'wb') as f:
                pickle.dump(self.bm25, f)
            
            self.logger.info("Built and saved BM25 index to %s", self.bm25_file)

        except Exception as e:
            self.logger.error("Failed to build BM25 index: %s", e)
            raise

    def bm25_search(self, query: str, min_score: float = 0.0, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Perform BM25 keyword-based search on chunks
        
        Args:
            query (str): Search query
            min_score (float): Minimum BM25 score threshold
            max_results (int): Maximum number of results to return
            
        Returns:
            List[Dict]: Results with BM25 scores and chunk content
        """
        if self.bm25 is None:
            raise ValueError("BM25 index not found. Call build_bm25_index() first.")
        
        if not query.strip():
            return []

        # 1. Tokenize query
        self.logger.info("BM25 searching for: '%s'", query)
        query_tokens = query.lower().split()
        
        # 2. Get BM25 scores for all documents
        scores = self.bm25.get_scores(query_tokens)
        
        # 3. Create scored results
        scored_results = []
        for idx, score in enumerate(scores):
            if score >= min_score:
                row_data = {}
                if self.df is not None and idx < len(self.df):
                    row_data = {
                        "row_index": int(idx),
                        "full_row": self.df.iloc[idx].to_dict(),
                    }
                
                scored_results.append({
                    "bm25_score": float(score),
                    "chunk": self.chunks[idx],
                    "chunk_index": int(idx),
                    "preview": (self.chunks[idx][:150] + "..." 
                             if len(self.chunks[idx]) > 150 else self.chunks[idx]),
                    **row_data
                })

        # 4. Sort by BM25 score (descending) and limit results
        scored_results.sort(key=lambda x: x['bm25_score'], reverse=True)
        final_results = scored_results[:max_results]

        if not final_results:
            self.logger.warning("No BM25 results found above score threshold %.2f", min_score)
        else:
            self.logger.info("BM25 search returned %d results", len(final_results))

        return final_results


    def search(self, query: str, min_similarity: float = 0.55, max_results: int = 7) -> List[Dict[str, Any]]:
        """
        Find all chunks with similarity above threshold, return up to max_results.
        
        Args:
            query (str): Search query
            min_similarity (float): Minimum similarity threshold (0.0-1.0)
            max_results (int): Maximum number of results to return
        
        Returns:
            List[Dict]: Results with similarity scores and chunk content
        """
        if self.embeddings is None:
            raise ValueError("Embeddings not found. Run create_embeddings() first.")
        
        # Load FAISS index if not already loaded
        if self.faiss_index is None:
            if not self._load_faiss_index():
                raise ValueError("FAISS index not found. Run create_embeddings() first.")
        
        if not query.strip():
            return []
        
        # 1. Encode the query using the same model
        self.logger.info("Searching for: '%s'", query)
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        
        # 2. Normalize query embedding for cosine similarity
        query_embedding = query_embedding.astype(np.float32)
        faiss.normalize_L2(query_embedding)
        
        # 3. Use FAISS for ultra-fast similarity search
        # Search for more results to ensure we capture all above threshold
        search_k = min(len(self.chunks), 50)  # Search more broadly
        similarities, indices = self.faiss_index.search(query_embedding, search_k)
        
        # FAISS returns 2D arrays, take the first row
        similarities = similarities[0]
        indices = indices[0]
        
        # 4. Collect ALL results above similarity threshold
        results = []
        for sim, idx in zip(similarities, indices):
            if sim >= min_similarity and idx != -1:  # -1 indicates no result
                
                # Get the corresponding row data from DataFrame if available
                row_data = {}
                if self.df is not None and idx < len(self.df):
                    row_data = {
                        "row_index": int(idx),
                        "full_row": self.df.iloc[idx].to_dict(),
                    }
                
                results.append({
                    "similarity": float(sim),
                    "chunk": self.chunks[idx],
                    "chunk_index": int(idx),
                    "preview": (self.chunks[idx][:150] + "..." 
                            if len(self.chunks[idx]) > 150 else self.chunks[idx]),
                    **row_data
                })
        
        # 5. Sort by similarity (highest first) and limit to max_results
        results.sort(key=lambda x: x['similarity'], reverse=True)
        final_results = results[:max_results]
        
        if not final_results:
            self.logger.warning("No results found above similarity threshold %.2f", min_similarity)
        else:
            self.logger.info("Found %d results above %.2f similarity (showing top %d)", 
                            len(results), min_similarity, len(final_results))
        
        return final_results
    
    def hybrid_search(self, query: str, 
                     semantic_weight: float = 0.7, 
                     bm25_weight: float = 0.3,
                     max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Combine semantic (FAISS) and lexical (BM25) search results
        
        Args:
            query (str): Search query
            semantic_weight (float): Weight for semantic similarity scores
            bm25_weight (float): Weight for BM25 scores  
            max_results (int): Maximum number of results to return
            
        Returns:
            List[Dict]: Hybrid search results with combined scores
        """
        # Get results from both search methods
        semantic_results = self.search(query, min_similarity=0.5, max_results=max_results*2)
        bm25_results = self.bm25_search(query, min_score=0.0, max_results=max_results*2)
        
        # Normalize scores for fair combination
        semantic_scores = {}
        bm25_scores = {}
        
        # Collect semantic scores
        max_sem_score = max([r['similarity'] for r in semantic_results], default=0)
        for result in semantic_results:
            idx = result['chunk_index']
            semantic_scores[idx] = result['similarity'] / max_sem_score if max_sem_score > 0 else 0
        
        # Collect BM25 scores  
        max_bm25_score = max([r['bm25_score'] for r in bm25_results], default=0)
        for result in bm25_results:
            idx = result['chunk_index']
            bm25_scores[idx] = result['bm25_score'] / max_bm25_score if max_bm25_score > 0 else 0

        # Combine scores
        all_indices = set(semantic_scores.keys()) | set(bm25_scores.keys())
        hybrid_results = []
        
        for idx in all_indices:
            sem_score = semantic_scores.get(idx, 0)
            bm25_score = bm25_scores.get(idx, 0)
            combined_score = (semantic_weight * sem_score) + (bm25_weight * bm25_score)
            
            # Get chunk data
            row_data = {}
            if self.df is not None and idx < len(self.df):
                row_data = {
                    "row_index": int(idx),
                    "full_row": self.df.iloc[idx].to_dict(),
                }
            
            hybrid_results.append({
                "combined_score": combined_score,
                "semantic_score": sem_score * max_sem_score if max_sem_score > 0 else 0,
                "bm25_score": bm25_score * max_bm25_score if max_bm25_score > 0 else 0,
                "chunk": self.chunks[idx],
                "chunk_index": int(idx),
                "preview": (self.chunks[idx][:150] + "..." 
                         if len(self.chunks[idx]) > 150 else self.chunks[idx]),
                **row_data
            })

        # Sort by combined score and return top results
        hybrid_results.sort(key=lambda x: x['combined_score'], reverse=True)
        final_results = hybrid_results[:max_results]
        
        self.logger.info("Hybrid search returned %d combined results", len(final_results))
        return final_results



logging.basicConfig(level=logging.INFO)

def retrieve_data_function(query, chunk_file="files/chunks.json"):
    rag = ExcelRAG(chunk_file)
    rag.load_excel("files/sample1.xlsx")
    rag.load_chunks()
    rag.create_embeddings()    # Load/create embeddings (cached!)
    rag.build_bm25_index()
    results = rag.hybrid_search(query)

    retrieved_chunks = [res["chunk"] for res in results]
    retrieved_data = "\n".join(retrieved_chunks)
    return retrieved_data, results


def referal_links(results):
    output = []
    for i in range(len(results)):
        link = results[i]["full_row"]["Link"]
        if link not in output:
            output.append(link)
            if len(output) == 3:
                break
    
    # Format as markdown links and join with commas
    if output:
        formatted_links = ", ".join([f"[{link}]({link})" for link in output])
        return f"Reference Links:\n{formatted_links}"
    else:
        return "Reference Links:\nNo reference links available."
    