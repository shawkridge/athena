package com.anthropic.semanticsearch.settings;

import com.intellij.openapi.components.PersistentStateComponent;
import com.intellij.openapi.components.Service;
import com.intellij.openapi.components.State;
import com.intellij.openapi.components.Storage;
import com.intellij.openapi.project.Project;
import com.intellij.util.xmlb.XmlSerializerUtil;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

/**
 * Plugin settings and configuration.
 */
@Service(Service.Level.PROJECT)
@State(
    name = "SemanticSearchSettings",
    storages = @Storage("semanticSearch.xml")
)
public class SearchSettings implements PersistentStateComponent<SearchSettings> {
    public String pythonPath = "python";
    public int backendPort = 5000;
    public String language = "auto";
    public String ragStrategy = "adaptive";
    public int resultLimit = 10;
    public double minScore = 0.3;
    public boolean autoIndex = true;
    public boolean useEmbeddings = true;
    public String embeddingProvider = "mock";

    public static SearchSettings getInstance(@NotNull Project project) {
        return project.getService(SearchSettings.class);
    }

    @Override
    public @Nullable SearchSettings getState() {
        return this;
    }

    @Override
    public void loadState(@NotNull SearchSettings state) {
        XmlSerializerUtil.copyBean(state, this);
    }

    // Getters and setters
    public String getPythonPath() {
        return pythonPath;
    }

    public void setPythonPath(String pythonPath) {
        this.pythonPath = pythonPath;
    }

    public int getBackendPort() {
        return backendPort;
    }

    public void setBackendPort(int backendPort) {
        this.backendPort = backendPort;
    }

    public String getLanguage() {
        return language;
    }

    public void setLanguage(String language) {
        this.language = language;
    }

    public String getRagStrategy() {
        return ragStrategy;
    }

    public void setRagStrategy(String ragStrategy) {
        this.ragStrategy = ragStrategy;
    }

    public int getResultLimit() {
        return resultLimit;
    }

    public void setResultLimit(int resultLimit) {
        this.resultLimit = Math.max(1, Math.min(100, resultLimit));
    }

    public double getMinScore() {
        return minScore;
    }

    public void setMinScore(double minScore) {
        this.minScore = Math.max(0, Math.min(1, minScore));
    }

    public boolean isAutoIndex() {
        return autoIndex;
    }

    public void setAutoIndex(boolean autoIndex) {
        this.autoIndex = autoIndex;
    }

    public boolean isUseEmbeddings() {
        return useEmbeddings;
    }

    public void setUseEmbeddings(boolean useEmbeddings) {
        this.useEmbeddings = useEmbeddings;
    }

    public String getEmbeddingProvider() {
        return embeddingProvider;
    }

    public void setEmbeddingProvider(String embeddingProvider) {
        this.embeddingProvider = embeddingProvider;
    }
}
