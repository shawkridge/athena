package com.anthropic.semanticsearch.ui;

import com.intellij.openapi.project.Project;
import com.intellij.openapi.fileEditor.FileEditorManager;
import com.intellij.openapi.fileEditor.OpenFileDescriptor;
import com.intellij.openapi.vfs.VirtualFileManager;
import com.intellij.openapi.vfs.VirtualFile;
import com.intellij.ui.components.JBList;
import com.intellij.ui.components.JBScrollPane;
import com.intellij.ui.table.JBTable;
import com.intellij.util.ui.JBUI;

import javax.swing.*;
import javax.swing.table.DefaultTableModel;
import java.awt.*;
import java.util.List;

import com.anthropic.semanticsearch.search.SearchResult;

/**
 * Tool window panel for displaying semantic search results.
 */
public class SearchToolWindow extends JPanel {
    private final Project project;
    private JBTable resultsTable;
    private JLabel infoLabel;

    public SearchToolWindow(Project project) {
        this.project = project;
        initializeUI();
    }

    private void initializeUI() {
        setLayout(new BorderLayout(0, 10));
        setBorder(JBUI.Borders.empty(10));

        // Info panel
        infoLabel = new JLabel("No search performed yet");
        infoLabel.setFont(infoLabel.getFont().deriveFont(Font.ITALIC));
        add(infoLabel, BorderLayout.NORTH);

        // Results table
        resultsTable = new JBTable();
        resultsTable.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
        resultsTable.addMouseListener(new java.awt.event.MouseAdapter() {
            @Override
            public void mouseClicked(java.awt.event.MouseEvent event) {
                if (event.getClickCount() == 2) {
                    openSelectedResult();
                }
            }
        });

        JBScrollPane scrollPane = new JBScrollPane(resultsTable);
        add(scrollPane, BorderLayout.CENTER);
    }

    /**
     * Display search results.
     */
    public void showResults(List<SearchResult> results, String query, boolean useRAG) {
        // Update info label
        String ragInfo = useRAG ? " (with RAG)" : "";
        infoLabel.setText(String.format("Query: %s%s - Found %d results", query, ragInfo, results.size()));

        // Create table model
        DefaultTableModel model = new DefaultTableModel();
        model.addColumn("Name");
        model.addColumn("Type");
        model.addColumn("File");
        model.addColumn("Line");
        model.addColumn("Score");

        // Add results to table
        for (SearchResult result : results) {
            model.addRow(new Object[]{
                result.getName(),
                result.getType(),
                result.getFile(),
                result.getLine(),
                String.format("%.1f%%", result.getRelevance() * 100)
            });
        }

        resultsTable.setModel(model);

        // Adjust column widths
        resultsTable.getColumnModel().getColumn(0).setPreferredWidth(200);
        resultsTable.getColumnModel().getColumn(1).setPreferredWidth(80);
        resultsTable.getColumnModel().getColumn(2).setPreferredWidth(300);
        resultsTable.getColumnModel().getColumn(3).setPreferredWidth(60);
        resultsTable.getColumnModel().getColumn(4).setPreferredWidth(80);
    }

    /**
     * Open the selected search result in editor.
     */
    private void openSelectedResult() {
        int row = resultsTable.getSelectedRow();
        if (row < 0) {
            return;
        }

        String filePath = (String) resultsTable.getValueAt(row, 2);
        int lineNumber = Integer.parseInt((String) resultsTable.getValueAt(row, 3).toString());

        VirtualFile file = VirtualFileManager.getInstance().findFileByUrl("file://" + filePath);
        if (file != null) {
            OpenFileDescriptor descriptor = new OpenFileDescriptor(project, file, lineNumber - 1, 0);
            FileEditorManager.getInstance(project).openTextEditor(descriptor, true);
        }
    }
}
