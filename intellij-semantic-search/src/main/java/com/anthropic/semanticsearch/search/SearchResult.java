package com.anthropic.semanticsearch.search;

/**
 * Represents a semantic search result.
 */
public class SearchResult {
    private final String name;
    private final String type;
    private final String file;
    private final int line;
    private final double relevance;
    private final String docstring;

    public SearchResult(String name, String type, String file, int line, double relevance, String docstring) {
        this.name = name;
        this.type = type;
        this.file = file;
        this.line = line;
        this.relevance = relevance;
        this.docstring = docstring;
    }

    public String getName() {
        return name;
    }

    public String getType() {
        return type;
    }

    public String getFile() {
        return file;
    }

    public int getLine() {
        return line;
    }

    public double getRelevance() {
        return relevance;
    }

    public String getDocstring() {
        return docstring;
    }

    @Override
    public String toString() {
        return String.format("%s (%s) at %s:%d [%.1f%%]", name, type, file, line, relevance * 100);
    }
}
