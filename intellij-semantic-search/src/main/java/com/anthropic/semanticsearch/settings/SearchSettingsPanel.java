package com.anthropic.semanticsearch.settings;

import com.intellij.ui.components.JBLabel;
import com.intellij.util.ui.FormBuilder;
import com.intellij.util.ui.JBUI;

import javax.swing.*;

/**
 * UI panel for semantic search settings.
 */
public class SearchSettingsPanel {
    private final JPanel panel;
    private final JTextField pythonPathField;
    private final JSpinner backendPortSpinner;
    private final JComboBox<String> languageCombo;
    private final JComboBox<String> ragStrategyCombo;
    private final JSpinner resultLimitSpinner;
    private final JSpinner minScoreSpinner;
    private final JCheckBox autoIndexCheckbox;
    private final JCheckBox useEmbeddingsCheckbox;
    private final JComboBox<String> embeddingProviderCombo;

    public SearchSettingsPanel(SearchSettings settings) {
        pythonPathField = new JTextField(settings.getPythonPath());
        backendPortSpinner = new JSpinner(new SpinnerNumberModel(settings.getBackendPort(), 1024, 65535, 1));
        languageCombo = new JComboBox<>(new String[]{"auto", "python", "javascript", "typescript", "java", "go"});
        languageCombo.setSelectedItem(settings.getLanguage());
        ragStrategyCombo = new JComboBox<>(new String[]{"adaptive", "self", "corrective", "direct"});
        ragStrategyCombo.setSelectedItem(settings.getRagStrategy());
        resultLimitSpinner = new JSpinner(new SpinnerNumberModel(settings.getResultLimit(), 1, 100, 1));
        minScoreSpinner = new JSpinner(new SpinnerNumberModel(settings.getMinScore(), 0.0, 1.0, 0.1));
        autoIndexCheckbox = new JCheckBox("Auto-index workspace on startup", settings.isAutoIndex());
        useEmbeddingsCheckbox = new JCheckBox("Use embeddings (semantic search)", settings.isUseEmbeddings());
        embeddingProviderCombo = new JComboBox<>(new String[]{"mock", "ollama", "anthropic"});
        embeddingProviderCombo.setSelectedItem(settings.getEmbeddingProvider());

        panel = FormBuilder.createFormBuilder()
            .addLabeledComponent(new JBLabel("Python Path:"), pythonPathField)
            .addLabeledComponent(new JBLabel("Backend Port:"), backendPortSpinner)
            .addLabeledComponent(new JBLabel("Language:"), languageCombo)
            .addLabeledComponent(new JBLabel("RAG Strategy:"), ragStrategyCombo)
            .addLabeledComponent(new JBLabel("Result Limit:"), resultLimitSpinner)
            .addLabeledComponent(new JBLabel("Min Score:"), minScoreSpinner)
            .addComponent(autoIndexCheckbox)
            .addComponent(useEmbeddingsCheckbox)
            .addLabeledComponent(new JBLabel("Embedding Provider:"), embeddingProviderCombo)
            .addComponentFillVertically(new JPanel(), 0)
            .getPanel();

        panel.setBorder(JBUI.Borders.empty(10));
    }

    public JPanel getPanel() {
        return panel;
    }

    public boolean isModified(SearchSettings settings) {
        return !pythonPathField.getText().equals(settings.getPythonPath())
            || (int) backendPortSpinner.getValue() != settings.getBackendPort()
            || !languageCombo.getSelectedItem().equals(settings.getLanguage())
            || !ragStrategyCombo.getSelectedItem().equals(settings.getRagStrategy())
            || (int) resultLimitSpinner.getValue() != settings.getResultLimit()
            || (double) minScoreSpinner.getValue() != settings.getMinScore()
            || autoIndexCheckbox.isSelected() != settings.isAutoIndex()
            || useEmbeddingsCheckbox.isSelected() != settings.isUseEmbeddings()
            || !embeddingProviderCombo.getSelectedItem().equals(settings.getEmbeddingProvider());
    }

    public void apply(SearchSettings settings) {
        settings.setPythonPath(pythonPathField.getText());
        settings.setBackendPort((int) backendPortSpinner.getValue());
        settings.setLanguage((String) languageCombo.getSelectedItem());
        settings.setRagStrategy((String) ragStrategyCombo.getSelectedItem());
        settings.setResultLimit((int) resultLimitSpinner.getValue());
        settings.setMinScore((double) minScoreSpinner.getValue());
        settings.setAutoIndex(autoIndexCheckbox.isSelected());
        settings.setUseEmbeddings(useEmbeddingsCheckbox.isSelected());
        settings.setEmbeddingProvider((String) embeddingProviderCombo.getSelectedItem());
    }

    public void reset(SearchSettings settings) {
        pythonPathField.setText(settings.getPythonPath());
        backendPortSpinner.setValue(settings.getBackendPort());
        languageCombo.setSelectedItem(settings.getLanguage());
        ragStrategyCombo.setSelectedItem(settings.getRagStrategy());
        resultLimitSpinner.setValue(settings.getResultLimit());
        minScoreSpinner.setValue(settings.getMinScore());
        autoIndexCheckbox.setSelected(settings.isAutoIndex());
        useEmbeddingsCheckbox.setSelected(settings.isUseEmbeddings());
        embeddingProviderCombo.setSelectedItem(settings.getEmbeddingProvider());
    }
}
