import axios, { AxiosInstance } from 'axios';
import * as vscode from 'vscode';
import { BackendManager } from './backendManager';

export interface SearchResult {
    file: string;
    line: number;
    name: string;
    type: string;
    signature: string;
    relevance: number;
    docstring?: string;
    code?: string;
}

export interface SearchResponse {
    results: SearchResult[];
    query: string;
    strategy: string;
    count: number;
    elapsed_ms: number;
}

export class SearchProvider {
    private client: AxiosInstance;
    private backendManager: BackendManager;

    constructor(backendManager: BackendManager) {
        this.backendManager = backendManager;
        const config = vscode.workspace.getConfiguration('semanticSearch');
        const port = config.get('backendPort') as number || 5000;
        const baseURL = `http://localhost:${port}`;

        this.client = axios.create({
            baseURL,
            timeout: 30000,
        });
    }

    async search(query: string, useRAG: boolean): Promise<SearchResult[]> {
        try {
            const config = vscode.workspace.getConfiguration('semanticSearch');
            const strategy = useRAG ? config.get('ragStrategy') : 'direct';
            const limit = config.get('resultLimit') as number || 10;
            const minScore = config.get('minScore') as number || 0.3;

            const response = await this.client.post<SearchResponse>('/search', {
                query,
                strategy,
                limit,
                min_score: minScore,
                use_rag: useRAG,
            });

            return response.data.results;
        } catch (error) {
            if (axios.isAxiosError(error)) {
                throw new Error(`Search error: ${error.message}`);
            }
            throw error;
        }
    }

    async searchByType(type: string, query?: string): Promise<SearchResult[]> {
        try {
            const limit = vscode.workspace.getConfiguration('semanticSearch').get('resultLimit') as number || 10;

            const response = await this.client.post<SearchResponse>('/search/by-type', {
                type,
                query,
                limit,
            });

            return response.data.results;
        } catch (error) {
            if (axios.isAxiosError(error)) {
                throw new Error(`Search by type error: ${error.message}`);
            }
            throw error;
        }
    }

    async searchByName(name: string, exact: boolean = false): Promise<SearchResult[]> {
        try {
            const limit = vscode.workspace.getConfiguration('semanticSearch').get('resultLimit') as number || 10;

            const response = await this.client.post<SearchResponse>('/search/by-name', {
                name,
                exact,
                limit,
            });

            return response.data.results;
        } catch (error) {
            if (axios.isAxiosError(error)) {
                throw new Error(`Search by name error: ${error.message}`);
            }
            throw error;
        }
    }

    async findDependencies(filePath: string, unitName: string): Promise<SearchResult[]> {
        try {
            const response = await this.client.post<SearchResponse>('/dependencies', {
                file_path: filePath,
                unit_name: unitName,
            });

            return response.data.results;
        } catch (error) {
            if (axios.isAxiosError(error)) {
                throw new Error(`Dependency search error: ${error.message}`);
            }
            throw error;
        }
    }

    async getFileAnalysis(filePath: string): Promise<any> {
        try {
            const response = await this.client.get(`/analyze?file=${encodeURIComponent(filePath)}`);
            return response.data;
        } catch (error) {
            if (axios.isAxiosError(error)) {
                throw new Error(`File analysis error: ${error.message}`);
            }
            throw error;
        }
    }

    async getStatistics(): Promise<any> {
        try {
            const response = await this.client.get('/statistics');
            return response.data;
        } catch (error) {
            if (axios.isAxiosError(error)) {
                throw new Error(`Statistics error: ${error.message}`);
            }
            throw error;
        }
    }
}
