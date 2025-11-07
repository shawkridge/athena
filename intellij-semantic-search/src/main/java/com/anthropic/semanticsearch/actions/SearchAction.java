package com.anthropic.semanticsearch.actions;

import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.wm.ToolWindowManager;
import com.intellij.openapi.diagnostic.Logger;
import org.jetbrains.annotations.NotNull;

import com.anthropic.semanticsearch.search.SearchProvider;
import com.anthropic.semanticsearch.search.SearchResult;
import com.anthropic.semanticsearch.ui.SearchToolWindow;
import com.anthropic.semanticsearch.settings.SearchSettings;

import java.util.List;

/**
 * Main semantic code search action.
 *
 * Triggered by Ctrl+Shift+F to open semantic search dialog.
 */
public class SearchAction extends AnAction {
    private static final Logger LOG = Logger.getInstance(SearchAction.class);

    @Override
    public void actionPerformed(@NotNull AnActionEvent event) {
        Project project = event.getProject();
        if (project == null) {
            Messages.showErrorDialog("No project open", "Semantic Search");
            return;
        }

        // Get search query from user
        String query = Messages.showInputDialog(
            project,
            "Enter search query:",
            "Semantic Code Search",
            Messages.getQuestionIcon(),
            "",
            null
        );

        if (query == null || query.trim().isEmpty()) {
            return;
        }

        performSearch(project, query, false);
    }

    /**
     * Perform semantic search with given query.
     */
    public static void performSearch(@NotNull Project project, @NotNull String query, boolean useRAG) {
        try {
            // Show progress
            Messages.showInfoMessage("Searching for: " + query, "Semantic Search");

            // Get search provider
            SearchProvider searchProvider = project.getService(SearchProvider.class);
            if (searchProvider == null || !searchProvider.isReady()) {
                Messages.showErrorDialog(
                    "Backend not ready. Please index workspace first.",
                    "Semantic Search"
                );
                return;
            }

            // Perform search
            List<SearchResult> results = searchProvider.search(query, useRAG);

            // Show results in tool window
            ToolWindowManager toolWindowManager = ToolWindowManager.getInstance(project);
            SearchToolWindow toolWindow = (SearchToolWindow) toolWindowManager
                .getToolWindow("Semantic Search")
                .getContentManager()
                .getContent(0)
                .getComponent();

            if (toolWindow != null) {
                toolWindow.showResults(results, query, useRAG);
            }

            LOG.info("Search completed: " + query + " -> " + results.size() + " results");
        } catch (Exception e) {
            LOG.error("Search failed", e);
            Messages.showErrorDialog("Search failed: " + e.getMessage(), "Semantic Search");
        }
    }

    @Override
    public void update(@NotNull AnActionEvent e) {
        Project project = e.getProject();
        e.getPresentation().setEnabled(project != null);
    }
}
