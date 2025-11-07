import * as vscode from 'vscode';
import * as cp from 'child_process';
import axios from 'axios';
import * as path from 'path';

export class BackendManager {
    private process: cp.ChildProcess | null = null;
    private context: vscode.ExtensionContext;
    private port: number;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        const config = vscode.workspace.getConfiguration('semanticSearch');
        this.port = config.get('backendPort') as number || 5000;
    }

    async startBackend(): Promise<void> {
        try {
            // Check if backend is already running
            try {
                await axios.get(`http://localhost:${this.port}/health`);
                console.log('Backend already running');
                return;
            } catch {
                // Backend not running, start it
            }

            // Get Python executable and backend script path
            const config = vscode.workspace.getConfiguration('semanticSearch');
            const pythonPath = config.get('pythonPath') as string || 'python';

            // Backend script should be in the extension's context
            const backendScript = path.join(this.context.extensionPath, 'backend', 'app.py');

            return new Promise((resolve, reject) => {
                this.process = cp.spawn(pythonPath, [backendScript, '--port', this.port.toString()], {
                    detached: true,
                    stdio: ['ignore', 'pipe', 'pipe'],
                });

                // Wait for backend to be ready
                let ready = false;
                const checkReady = setInterval(async () => {
                    try {
                        await axios.get(`http://localhost:${this.port}/health`);
                        ready = true;
                        clearInterval(checkReady);
                        resolve();
                    } catch {
                        // Still waiting
                    }
                }, 500);

                // Timeout after 10 seconds
                setTimeout(() => {
                    if (!ready) {
                        clearInterval(checkReady);
                        reject(new Error('Backend startup timeout'));
                    }
                }, 10000);

                this.process?.on('error', (error) => {
                    clearInterval(checkReady);
                    reject(error);
                });
            });
        } catch (error) {
            throw new Error(`Failed to start backend: ${error}`);
        }
    }

    stopBackend(): void {
        if (this.process) {
            try {
                process.kill(-this.process.pid!);
            } catch {
                // Process might already be dead
            }
        }
    }

    async indexWorkspace(workspacePath: string): Promise<{ files: number; units: number }> {
        try {
            const response = await axios.post(`http://localhost:${this.port}/index`, {
                path: workspacePath,
            });
            return response.data;
        } catch (error) {
            throw new Error(`Failed to index workspace: ${error}`);
        }
    }

    async getHealth(): Promise<{ status: string; indexed: boolean; units: number }> {
        try {
            const response = await axios.get(`http://localhost:${this.port}/health`);
            return response.data;
        } catch (error) {
            throw new Error(`Backend health check failed: ${error}`);
        }
    }
}
