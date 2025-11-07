package com.anthropic.semanticsearch.search;

import com.intellij.openapi.components.Service;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.diagnostic.Logger;
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonArray;

import java.net.HttpURLConnection;
import java.net.URL;
import java.io.OutputStream;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;

import com.anthropic.semanticsearch.settings.SearchSettings;

/**
 * Service for performing semantic searches via REST API.
 *
 * Communicates with Python backend on localhost.
 */
@Service(Service.Level.PROJECT)
public final class SearchProvider {
    private static final Logger LOG = Logger.getInstance(SearchProvider.class);
    private static final Gson gson = new Gson();

    private final Project project;
    private final SearchSettings settings;
    private boolean indexed = false;

    public SearchProvider(Project project) {
        this.project = project;
        this.settings = SearchSettings.getInstance(project);
    }

    /**
     * Check if backend is ready and indexed.
     */
    public boolean isReady() {
        try {
            String response = sendRequest("GET", "/health", null);
            JsonObject json = gson.fromJson(response, JsonObject.class);
            indexed = json.get("indexed").getAsBoolean();
            return indexed;
        } catch (Exception e) {
            LOG.debug("Backend not ready", e);
            return false;
        }
    }

    /**
     * Perform semantic search.
     */
    public List<SearchResult> search(String query, boolean useRAG) throws Exception {
        JsonObject requestBody = new JsonObject();
        requestBody.addProperty("query", query);
        requestBody.addProperty("strategy", "adaptive");
        requestBody.addProperty("limit", settings.getResultLimit());
        requestBody.addProperty("min_score", settings.getMinScore());
        requestBody.addProperty("use_rag", useRAG);

        String response = sendRequest("POST", "/search", requestBody.toString());
        JsonObject json = gson.fromJson(response, JsonObject.class);
        JsonArray results = json.getAsJsonArray("results");

        List<SearchResult> searchResults = new ArrayList<>();
        for (int i = 0; i < results.size(); i++) {
            JsonObject result = results.get(i).getAsJsonObject();
            searchResults.add(new SearchResult(
                result.get("name").getAsString(),
                result.get("type").getAsString(),
                result.get("file").getAsString(),
                result.get("line").getAsInt(),
                result.get("relevance").getAsDouble(),
                result.has("docstring") ? result.get("docstring").getAsString() : null
            ));
        }

        return searchResults;
    }

    /**
     * Search by code unit type.
     */
    public List<SearchResult> searchByType(String type, String query) throws Exception {
        JsonObject requestBody = new JsonObject();
        requestBody.addProperty("type", type);
        if (query != null && !query.isEmpty()) {
            requestBody.addProperty("query", query);
        }
        requestBody.addProperty("limit", settings.getResultLimit());

        String response = sendRequest("POST", "/search/by-type", requestBody.toString());
        JsonObject json = gson.fromJson(response, JsonObject.class);
        JsonArray results = json.getAsJsonArray("results");

        List<SearchResult> searchResults = new ArrayList<>();
        for (int i = 0; i < results.size(); i++) {
            JsonObject result = results.get(i).getAsJsonObject();
            searchResults.add(new SearchResult(
                result.get("name").getAsString(),
                result.get("type").getAsString(),
                result.get("file").getAsString(),
                result.get("line").getAsInt(),
                result.get("relevance").getAsDouble(),
                result.has("docstring") ? result.get("docstring").getAsString() : null
            ));
        }

        return searchResults;
    }

    /**
     * Index workspace.
     */
    public void indexWorkspace(String projectPath) throws Exception {
        JsonObject requestBody = new JsonObject();
        requestBody.addProperty("path", projectPath);

        String response = sendRequest("POST", "/index", requestBody.toString());
        JsonObject json = gson.fromJson(response, JsonObject.class);

        indexed = true;
        LOG.info("Indexed " + json.get("units").getAsInt() + " units from " +
                json.get("files").getAsInt() + " files");
    }

    /**
     * Send HTTP request to backend.
     */
    private String sendRequest(String method, String endpoint, String body) throws Exception {
        int port = settings.getBackendPort();
        String url = "http://localhost:" + port + endpoint;

        HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
        connection.setRequestMethod(method);
        connection.setRequestProperty("Content-Type", "application/json");
        connection.setConnectTimeout(5000);
        connection.setReadTimeout(30000);

        if (body != null) {
            connection.setDoOutput(true);
            try (OutputStream os = connection.getOutputStream()) {
                os.write(body.getBytes());
            }
        }

        StringBuilder response = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(connection.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                response.append(line);
            }
        }

        return response.toString();
    }
}
