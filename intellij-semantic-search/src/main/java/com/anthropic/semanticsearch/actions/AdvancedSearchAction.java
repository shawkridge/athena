package com.anthropic.semanticsearch.actions;

import com.anthropic.semanticsearch.search.SearchProvider;
import com.anthropic.semanticsearch.search.SearchResult;
import com.anthropic.semanticsearch.ui.SearchToolWindow;
import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.wm.ToolWindow;
import com.intellij.openapi.wm.ToolWindowManager;
import org.jetbrains.annotations.NotNull;

import java.util.List;

/**
 * Action for advanced semantic search with RAG strategies enabled.
 * Triggered by Ctrl+Shift+Alt+F
 *
 * RAG (Retrieval-Augmented Generation) strategies:
 * - Self-RAG: Evaluates relevance of retrieved documents
 * - Corrective RAG: Iteratively refines queries if results are poor
 * - Adaptive RAG: Automatically selects best strategy based on query complexity
 */
public class AdvancedSearchAction extends AnAction {

    @Override
    public void actionPerformed(@NotNull AnActionEvent e) {
        Project project = e.getProject();
        if (project == null) {
            Messages.showErrorDialog("No project open", "Semantic Code Search");
            return;
        }

        // Prompt user for search query
        String query = Messages.showInputDialog(
            project,
            "Enter advanced search query (with RAG strategies):",
            "Advanced Semantic Code Search",
            Messages.getQuestionIcon(),
            "",
            null
        );

        if (query != null && !query.trim().isEmpty()) {
            performAdvancedSearch(project, query.trim());
        }
    }

    /**
     * Performs advanced semantic search using RAG strategies.
     * RAG combines retrieval with ranking and evaluation for better results.
     */
    private static void performAdvancedSearch(Project project, String query) {
        SearchProvider searchProvider = project.getService(SearchProvider.class);

        new Thread(() -> {
            try {
                // Check if backend is ready
                if (!searchProvider.isReady()) {
                    Messages.showErrorDialog(
                        "Backend not ready. Please wait or restart.",
                        "Semantic Code Search"
                    );
                    return;
                }

                // Perform search with RAG enabled
                List<SearchResult> results = searchProvider.search(query, true);

                // Show results in tool window
                ToolWindowManager toolWindowManager = ToolWindowManager.getInstance(project);
                ToolWindow toolWindow = toolWindowManager.getToolWindow("Semantic Search");
                if (toolWindow != null) {
                    SearchToolWindow searchPanel = (SearchToolWindow) toolWindow.getContentManager()
                        .getContent(0)
                        .getComponent();
                    searchPanel.showResults(results, query, true);
                    toolWindow.activate(null);
                }
            } catch (Exception ex) {
                Messages.showErrorDialog(
                    "Advanced search failed: " + ex.getMessage(),
                    "Semantic Code Search"
                );
            }
        }).start();
    }

    @Override
    public void update(@NotNull AnActionEvent e) {
        Project project = e.getProject();
        e.getPresentation().setEnabled(project != null);
    }
}
