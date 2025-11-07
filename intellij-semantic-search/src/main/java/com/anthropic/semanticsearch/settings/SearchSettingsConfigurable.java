package com.anthropic.semanticsearch.settings;

import com.intellij.openapi.options.Configurable;
import com.intellij.openapi.project.Project;
import org.jetbrains.annotations.Nls;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;

/**
 * Settings UI for semantic search configuration.
 */
public class SearchSettingsConfigurable implements Configurable {
    private final SearchSettings settings;
    private SearchSettingsPanel settingsPanel;

    public SearchSettingsConfigurable(Project project) {
        this.settings = SearchSettings.getInstance(project);
    }

    @Nls(capitalization = Nls.Capitalization.Title)
    @Override
    public String getDisplayName() {
        return "Semantic Code Search";
    }

    @Nullable
    @Override
    public JComponent createComponent() {
        settingsPanel = new SearchSettingsPanel(settings);
        return settingsPanel.getPanel();
    }

    @Override
    public boolean isModified() {
        return settingsPanel != null && settingsPanel.isModified(settings);
    }

    @Override
    public void apply() {
        if (settingsPanel != null) {
            settingsPanel.apply(settings);
        }
    }

    @Override
    public void reset() {
        if (settingsPanel != null) {
            settingsPanel.reset(settings);
        }
    }

    @Override
    public void disposeUIResources() {
        settingsPanel = null;
    }
}
