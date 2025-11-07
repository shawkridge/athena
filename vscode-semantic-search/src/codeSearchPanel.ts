import * as vscode from 'vscode';
import { SearchResult } from './searchProvider';

export class CodeSearchPanel {
    private panel: vscode.WebviewPanel | undefined;
    private context: vscode.ExtensionContext;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
    }

    show(results: SearchResult[], query: string, useRAG: boolean = false): void {
        if (!this.panel) {
            this.panel = vscode.window.createWebviewPanel(
                'semanticSearchResults',
                'Semantic Search Results',
                vscode.ViewColumn.Beside,
                {
                    enableScripts: true,
                    localResourceRoots: [vscode.Uri.file(this.context.extensionPath)],
                }
            );

            this.panel.onDidDispose(() => {
                this.panel = undefined;
            });
        }

        this.panel.webview.html = this.getWebviewContent(results, query, useRAG);
        this.panel.reveal();
    }

    private getWebviewContent(results: SearchResult[], query: string, useRAG: boolean): string {
        const resultsHtml = results.map((result, index) => `
            <div class="result" onclick="goToFile('${escapeHtml(result.file)}', ${result.line})">
                <div class="result-header">
                    <span class="result-name">${escapeHtml(result.name)}</span>
                    <span class="result-type ${result.type}">${result.type}</span>
                    <span class="result-score">${(result.relevance * 100).toFixed(1)}%</span>
                </div>
                <div class="result-file">${escapeHtml(result.file)}:${result.line}</div>
                ${result.docstring ? `<div class="result-doc">${escapeHtml(result.docstring)}</div>` : ''}
                ${result.signature ? `<div class="result-sig"><code>${escapeHtml(result.signature)}</code></div>` : ''}
            </div>
        `).join('');

        return `
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    * {
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }

                    body {
                        font-family: var(--vscode-font-family);
                        color: var(--vscode-foreground);
                        background-color: var(--vscode-editor-background);
                        padding: 10px;
                    }

                    .search-info {
                        padding: 10px;
                        background-color: var(--vscode-editor-selectionBackground);
                        border-radius: 4px;
                        margin-bottom: 10px;
                    }

                    .search-query {
                        font-weight: bold;
                        margin-bottom: 5px;
                    }

                    .search-meta {
                        font-size: 12px;
                        color: var(--vscode-descriptionForeground);
                    }

                    .rag-badge {
                        display: inline-block;
                        background-color: var(--vscode-statusBar-background);
                        color: var(--vscode-statusBar-foreground);
                        padding: 2px 6px;
                        border-radius: 3px;
                        font-size: 11px;
                        margin-left: 10px;
                    }

                    .results-container {
                        display: flex;
                        flex-direction: column;
                        gap: 8px;
                    }

                    .result {
                        padding: 10px;
                        background-color: var(--vscode-editor-inactiveSelectionBackground);
                        border-left: 3px solid var(--vscode-inputValidation-infoBorder);
                        border-radius: 4px;
                        cursor: pointer;
                        transition: all 0.2s ease;
                    }

                    .result:hover {
                        background-color: var(--vscode-editor-selectionBackground);
                        border-left-color: var(--vscode-inputValidation-infoBackground);
                    }

                    .result-header {
                        display: flex;
                        align-items: center;
                        gap: 10px;
                        margin-bottom: 5px;
                    }

                    .result-name {
                        font-weight: bold;
                        color: var(--vscode-symbolIcon-functionForeground);
                    }

                    .result-type {
                        display: inline-block;
                        padding: 2px 6px;
                        border-radius: 3px;
                        font-size: 11px;
                        font-weight: bold;
                    }

                    .result-type.function {
                        background-color: rgba(86, 156, 214, 0.2);
                        color: #569cd6;
                    }

                    .result-type.class {
                        background-color: rgba(78, 201, 176, 0.2);
                        color: #4ec9b0;
                    }

                    .result-type.import {
                        background-color: rgba(206, 145, 120, 0.2);
                        color: #ce9178;
                    }

                    .result-score {
                        margin-left: auto;
                        font-weight: bold;
                        color: var(--vscode-charts-green);
                        font-size: 12px;
                    }

                    .result-file {
                        font-size: 11px;
                        color: var(--vscode-descriptionForeground);
                        margin-bottom: 5px;
                    }

                    .result-doc {
                        font-size: 12px;
                        color: var(--vscode-foreground);
                        margin: 5px 0;
                        max-height: 60px;
                        overflow: hidden;
                        text-overflow: ellipsis;
                    }

                    .result-sig {
                        font-size: 11px;
                        background-color: rgba(0, 0, 0, 0.2);
                        padding: 5px;
                        border-radius: 3px;
                        overflow-x: auto;
                    }

                    .result-sig code {
                        font-family: var(--vscode-editor-font-family);
                        color: var(--vscode-editor-foreground);
                    }

                    .empty {
                        padding: 20px;
                        text-align: center;
                        color: var(--vscode-descriptionForeground);
                    }
                </style>
            </head>
            <body>
                <div class="search-info">
                    <div class="search-query">Query: <code>${escapeHtml(query)}</code></div>
                    <div class="search-meta">
                        Found ${results.length} result${results.length !== 1 ? 's' : ''}
                        ${useRAG ? '<span class="rag-badge">RAG Enabled</span>' : ''}
                    </div>
                </div>

                <div class="results-container">
                    ${results.length > 0 ? resultsHtml : '<div class="empty">No results found</div>'}
                </div>

                <script>
                    const vscode = acquireVsCodeApi();

                    function goToFile(file, line) {
                        vscode.postMessage({
                            command: 'openFile',
                            file: file,
                            line: line
                        });
                    }
                </script>
            </body>
            </html>
        `;
    }
}

function escapeHtml(text: string): string {
    const map: { [key: string]: string } = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, (m) => map[m]);
}
