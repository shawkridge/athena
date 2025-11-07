package com.anthropic.semanticsearch.actions;

import com.anthropic.semanticsearch.search.SearchProvider;
import com.anthropic.semanticsearch.search.SearchResult;
import com.anthropic.semanticsearch.ui.SearchToolWindow;
import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.actionSystem.CommonDataKeys;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.wm.ToolWindow;
import com.intellij.openapi.wm.ToolWindowManager;
import org.jetbrains.annotations.NotNull;

import java.util.List;

/**
 * Action to search the selected text in the current editor.
 * Triggered by Ctrl+Alt+F
 */
public class SearchSelectionAction extends AnAction {

    @Override
    public void actionPerformed(@NotNull AnActionEvent e) {
        Project project = e.getProject();
        if (project == null) {
            Messages.showErrorDialog("No project open", "Semantic Code Search");
            return;
        }

        // Get the current editor and selected text
        Editor editor = e.getData(CommonDataKeys.EDITOR);
        if (editor == null) {
            Messages.showWarningDialog(
                "No text selected. Use Ctrl+Shift+F for manual search.",
                "Semantic Code Search"
            );
            return;
        }

        String selectedText = editor.getSelectionModel().getSelectedText();
        if (selectedText == null || selectedText.trim().isEmpty()) {
            Messages.showWarningDialog(
                "No text selected. Use Ctrl+Shift+F for manual search.",
                "Semantic Code Search"
            );
            return;
        }

        performSearch(project, selectedText.trim(), false);
    }

    /**
     * Performs semantic search on the selected text.
     */
    private static void performSearch(Project project, String query, boolean useRAG) {
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

                // Perform search
                List<SearchResult> results = searchProvider.search(query, useRAG);

                // Show results in tool window
                ToolWindowManager toolWindowManager = ToolWindowManager.getInstance(project);
                ToolWindow toolWindow = toolWindowManager.getToolWindow("Semantic Search");
                if (toolWindow != null) {
                    SearchToolWindow searchPanel = (SearchToolWindow) toolWindow.getContentManager()
                        .getContent(0)
                        .getComponent();
                    searchPanel.showResults(results, query, useRAG);
                    toolWindow.activate(null);
                }
            } catch (Exception ex) {
                Messages.showErrorDialog(
                    "Search failed: " + ex.getMessage(),
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
