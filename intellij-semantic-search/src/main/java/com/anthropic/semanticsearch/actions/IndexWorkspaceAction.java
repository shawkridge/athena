package com.anthropic.semanticsearch.actions;

import com.anthropic.semanticsearch.search.SearchProvider;
import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.project.ProjectManager;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.util.io.FileUtil;
import com.intellij.openapi.wm.WindowManager;
import org.jetbrains.annotations.NotNull;

import java.io.File;

/**
 * Action to manually re-index the entire workspace.
 *
 * This action:
 * 1. Finds all source files in the project
 * 2. Sends them to the backend for indexing
 * 3. Shows progress and results
 *
 * Useful when:
 * - New files are added to the project
 * - Settings change (language support, etc.)
 * - Backend cache needs refresh
 */
public class IndexWorkspaceAction extends AnAction {

    @Override
    public void actionPerformed(@NotNull AnActionEvent e) {
        Project project = e.getProject();
        if (project == null) {
            Messages.showErrorDialog("No project open", "Semantic Code Search");
            return;
        }

        String projectPath = project.getBasePath();
        if (projectPath == null || projectPath.isEmpty()) {
            Messages.showErrorDialog("Cannot determine project path", "Semantic Code Search");
            return;
        }

        // Confirm action with user
        int result = Messages.showYesNoDialog(
            project,
            "Re-index the entire workspace? This may take a few moments.",
            "Re-Index Workspace",
            "Re-Index",
            "Cancel",
            Messages.getQuestionIcon()
        );

        if (result == Messages.YES) {
            performIndexing(project, projectPath);
        }
    }

    /**
     * Performs workspace re-indexing in a background thread.
     */
    private static void performIndexing(Project project, String projectPath) {
        SearchProvider searchProvider = project.getService(SearchProvider.class);

        // Show progress dialog
        Messages.showInfoMessage(
            "Re-indexing workspace...\nThis may take a few moments.",
            "Semantic Code Search"
        );

        new Thread(() -> {
            try {
                // Check if backend is ready
                if (!searchProvider.isReady()) {
                    Messages.showErrorDialog(
                        "Backend not ready. Please check logs.",
                        "Semantic Code Search"
                    );
                    return;
                }

                // Get total file count for progress estimation
                int fileCount = countSourceFiles(projectPath);

                // Send indexing request to backend
                searchProvider.indexWorkspace(projectPath);

                // Show success message
                Messages.showInfoMessage(
                    String.format("Successfully indexed %d source files in workspace.", fileCount),
                    "Re-Index Complete"
                );
            } catch (Exception ex) {
                Messages.showErrorDialog(
                    "Indexing failed: " + ex.getMessage(),
                    "Semantic Code Search"
                );
            }
        }).start();
    }

    /**
     * Recursively counts source files in the project directory.
     * Supports: Python, JavaScript, TypeScript, Java, Go
     */
    private static int countSourceFiles(String projectPath) {
        int count = 0;
        String[] extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go"};

        try {
            File rootDir = new File(projectPath);
            if (rootDir.isDirectory()) {
                count = countFilesRecursive(rootDir, extensions);
            }
        } catch (Exception ignored) {
            // Return 0 if error occurs
        }

        return count;
    }

    /**
     * Recursively counts files with supported extensions.
     */
    private static int countFilesRecursive(File dir, String[] extensions) {
        int count = 0;

        // Skip common non-source directories
        String dirName = dir.getName();
        if (dirName.startsWith(".") ||
            "node_modules".equals(dirName) ||
            "venv".equals(dirName) ||
            "env".equals(dirName) ||
            "build".equals(dirName) ||
            "dist".equals(dirName) ||
            "target".equals(dirName)) {
            return 0;
        }

        File[] files = dir.listFiles();
        if (files == null) {
            return 0;
        }

        for (File file : files) {
            if (file.isDirectory()) {
                count += countFilesRecursive(file, extensions);
            } else if (file.isFile()) {
                String fileName = file.getName();
                for (String ext : extensions) {
                    if (fileName.endsWith(ext)) {
                        count++;
                        break;
                    }
                }
            }
        }

        return count;
    }

    @Override
    public void update(@NotNull AnActionEvent e) {
        Project project = e.getProject();
        e.getPresentation().setEnabled(project != null);
    }
}
