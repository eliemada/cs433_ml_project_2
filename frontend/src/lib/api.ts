/**
 * RAG Search API client
 */

// API base URL - configure based on environment
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface SearchResult {
    chunk_id: string;
    paper_id: string;
    paper_title: string;
    text: string;
    section_hierarchy: string[];
    score: number;
    rank: number;
}

export interface SearchResponse {
    query: string;
    results: SearchResult[];
    total_results: number;
    elapsed_ms: number;
}

export interface SearchRequest {
    query: string;
    top_k?: number;
    use_reranker?: boolean;
}

/**
 * Search for relevant document chunks
 */
export async function searchDocuments(request: SearchRequest): Promise<SearchResponse> {
    const response = await fetch(`${API_BASE_URL}/search`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            query: request.query,
            top_k: request.top_k ?? 10,
            use_reranker: request.use_reranker ?? true,
        }),
    });

    if (!response.ok) {
        throw new Error(`Search failed: ${response.status} ${response.statusText}`);
    }

    return response.json();
}

/**
 * Check API health
 */
export async function checkHealth(): Promise<{ status: string; index_loaded: boolean; index_size: number }> {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (!response.ok) {
        throw new Error('API health check failed');
    }
    return response.json();
}

// ============================================================================
// Chat API (RAG with LLM generation)
// ============================================================================

export interface ChatCitation {
    id: string;
    title: string;
    authors: string;
    year: string;
    snippet: string;
}

export interface ChatRequest {
    message: string;
    top_k?: number;
    use_reranker?: boolean;
    model?: 'gpt-4o-mini' | 'gpt-4o';
}

export interface ChatResponse {
    message: string;
    answer: string;
    sources_used: number;
    citations: ChatCitation[];
    elapsed_ms: number;
}

/**
 * Send a policy question and get a structured, evidence-based answer
 */
export async function chatWithRAG(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: request.message,
            top_k: request.top_k ?? 10,
            use_reranker: request.use_reranker ?? true,
            model: request.model ?? 'gpt-4o-mini',
        }),
    });

    if (!response.ok) {
        throw new Error(`Chat failed: ${response.status} ${response.statusText}`);
    }

    return response.json();
}

// ============================================================================
// PDF API
// ============================================================================

export interface PdfUrlResponse {
    paper_id: string;
    pdf_url: string;
    expires_in: number;
}

/**
 * Get a presigned URL to view/download a PDF
 */
export async function getPdfUrl(paperId: string): Promise<PdfUrlResponse> {
    const response = await fetch(`${API_BASE_URL}/pdf/${paperId}`);

    if (!response.ok) {
        throw new Error(`PDF not found: ${response.status}`);
    }

    return response.json();
}
