import * as vscode from 'vscode';
import axios from 'axios';
import { SearchProvider } from './searchProvider';
import { CodeSearchPanel } from './codeSearchPanel';
import { BackendManager } from './backendManager';

let backendManager: BackendManager;
let searchProvider: SearchProvider;
let resultsPanel: CodeSearchPanel | undefined;

export async function activate(context: vscode.ExtensionContext) {
    console.log('Semantic Code Search extension activated');

    // Initialize backend manager
    backendManager = new BackendManager(context);

    // Initialize search provider
    searchProvider = new SearchProvider(backendManager);

    // Register commands
    const commands = [
        vscode.commands.registerCommand('semantic-search.search', () => handleSearch(context, false)),
        vscode.commands.registerCommand('semantic-search.searchSelection', () => handleSearch(context, true)),
        vscode.commands.registerCommand('semantic-search.advancedSearch', () => handleAdvancedSearch(context)),
        vscode.commands.registerCommand('semantic-search.indexWorkspace', () => handleIndexWorkspace()),
        vscode.commands.registerCommand('semantic-search.toggleRAG', () => handleToggleRAG()),
        vscode.commands.registerCommand('semantic-search.openSettings', () => handleOpenSettings()),
    ];

    context.subscriptions.push(...commands);

    // Start backend
    try {
        await backendManager.startBackend();
        vscode.window.showInformationMessage('Semantic Code Search ready');
    } catch (error) {
        vscode.window.showErrorMessage(`Failed to start backend: ${error}`);
    }

    // Auto-index workspace if enabled
    const config = vscode.workspace.getConfiguration('semanticSearch');
    if (config.get('autoIndex') && vscode.workspace.workspaceFolders) {
        await handleIndexWorkspace();
    }
}

async function handleSearch(context: vscode.ExtensionContext, useSelection: boolean) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active editor');
        return;
    }

    let query: string | undefined;

    if (useSelection && editor.selection) {
        query = editor.document.getText(editor.selection);
    } else {
        query = await vscode.window.showInputBox({
            prompt: 'Enter search query',
            placeHolder: 'e.g., authenticate user',
        });
    }

    if (!query) {
        return;
    }

    try {
        vscode.window.showInformationMessage(`Searching for: ${query}`);

        const results = await searchProvider.search(query, false);

        // Show results in panel
        if (!resultsPanel) {
            resultsPanel = new CodeSearchPanel(context);
        }
        resultsPanel.show(results, query);

        vscode.commands.executeCommand('setContext', 'semantic-search:resultsAvailable', true);
    } catch (error) {
        vscode.window.showErrorMessage(`Search failed: ${error}`);
    }
}

async function handleAdvancedSearch(context: vscode.ExtensionContext) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active editor');
        return;
    }

    const query = await vscode.window.showInputBox({
        prompt: 'Enter advanced search query (will use RAG)',
        placeHolder: 'e.g., find authentication pattern',
    });

    if (!query) {
        return;
    }

    try {
        vscode.window.showInformationMessage(`Advanced search for: ${query}`);

        const results = await searchProvider.search(query, true);

        // Show results in panel
        if (!resultsPanel) {
            resultsPanel = new CodeSearchPanel(context);
        }
        resultsPanel.show(results, query, true);

        vscode.commands.executeCommand('setContext', 'semantic-search:resultsAvailable', true);
    } catch (error) {
        vscode.window.showErrorMessage(`Advanced search failed: ${error}`);
    }
}

async function handleIndexWorkspace() {
    if (!vscode.workspace.workspaceFolders) {
        vscode.window.showErrorMessage('No workspace open');
        return;
    }

    const workspacePath = vscode.workspace.workspaceFolders[0].uri.fsPath;

    try {
        vscode.window.showInformationMessage('Indexing workspace...');

        const result = await backendManager.indexWorkspace(workspacePath);

        vscode.window.showInformationMessage(
            `Indexed ${result.units} units from ${result.files} files`
        );
    } catch (error) {
        vscode.window.showErrorMessage(`Indexing failed: ${error}`);
    }
}

async function handleToggleRAG() {
    const config = vscode.workspace.getConfiguration('semanticSearch');
    const current = config.get('ragStrategy') as string;

    const options = ['adaptive', 'self', 'corrective', 'direct'];
    const next = options[(options.indexOf(current) + 1) % options.length];

    await config.update('ragStrategy', next, vscode.ConfigurationTarget.Global);
    vscode.window.showInformationMessage(`RAG strategy changed to: ${next}`);
}

async function handleOpenSettings() {
    vscode.commands.executeCommand('workbench.action.openSettings', 'semanticSearch');
}

export function deactivate() {
    if (backendManager) {
        backendManager.stopBackend();
    }
}
