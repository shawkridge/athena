#!/usr/bin/env python3
"""
VS Code Extension Backend for Semantic Code Search

Provides REST API for VS Code extension to interface with
the semantic code search system.
"""

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from flask import Flask, request, jsonify
from flask_cors import CORS

# Import semantic search components
try:
    from athena.code_search.tree_sitter_search import TreeSitterCodeSearch
    from athena.code_search.advanced_rag import AdaptiveRAG, SelfRAG, CorrectiveRAG
except ImportError:
    import sys
    # Try to add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from athena.code_search.tree_sitter_search import TreeSitterCodeSearch
    from athena.code_search.advanced_rag import AdaptiveRAG, SelfRAG, CorrectiveRAG

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Global state
search_engine: Optional[TreeSitterCodeSearch] = None
adaptive_rag: Optional[AdaptiveRAG] = None
indexed = False
workspace_path: Optional[str] = None


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'indexed': indexed,
        'workspace': workspace_path,
        'units': search_engine.indexer.get_statistics()['total_units'] if search_engine else 0,
    })


@app.route('/index', methods=['POST'])
def index_workspace():
    """Index workspace for search."""
    global search_engine, adaptive_rag, indexed, workspace_path

    data = request.get_json()
    path = data.get('path')

    if not path or not Path(path).exists():
        return jsonify({'error': 'Invalid path'}), 400

    try:
        logger.info(f'Indexing workspace: {path}')
        workspace_path = path

        # Detect language from file extensions
        language = detect_language(path)

        # Create search engine
        search_engine = TreeSitterCodeSearch(path, language=language)
        stats = search_engine.build_index()

        # Initialize RAG
        adaptive_rag = AdaptiveRAG(search_engine)

        indexed = True

        logger.info(f'Indexed {stats["units_extracted"]} units from {stats["files_indexed"]} files')

        return jsonify({
            'units': stats['units_extracted'],
            'files': stats['files_indexed'],
            'time': stats['indexing_time'],
        })
    except Exception as e:
        logger.error(f'Indexing failed: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/search', methods=['POST'])
def search():
    """Perform semantic code search."""
    if not search_engine:
        return jsonify({'error': 'Workspace not indexed. Call /index first.'}), 400

    data = request.get_json()
    query = data.get('query')
    strategy = data.get('strategy', 'adaptive')
    limit = data.get('limit', 10)
    min_score = data.get('min_score', 0.3)
    use_rag = data.get('use_rag', True)

    if not query:
        return jsonify({'error': 'Query required'}), 400

    try:
        start = time.time()

        # Perform search
        if use_rag and strategy != 'direct':
            if strategy == 'adaptive':
                results = adaptive_rag.retrieve(query, limit=limit)
            elif strategy == 'self':
                self_rag = SelfRAG(search_engine)
                results = self_rag.retrieve_and_evaluate(query, limit=limit)
            elif strategy == 'corrective':
                corrective_rag = CorrectiveRAG(search_engine)
                results = corrective_rag.retrieve_with_correction(query, limit=limit)
            else:
                results = search_engine.search(query, top_k=limit, min_score=min_score)
        else:
            results = search_engine.search(query, top_k=limit, min_score=min_score)

        elapsed = (time.time() - start) * 1000

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                'file': result.unit.file_path,
                'line': result.unit.start_line,
                'name': result.unit.name,
                'type': result.unit.type,
                'signature': result.unit.signature,
                'relevance': result.relevance,
                'docstring': result.unit.docstring,
                'code': result.unit.code[:200] if result.unit.code else None,
            })

        logger.info(f'Search "{query}" -> {len(formatted_results)} results in {elapsed:.1f}ms')

        return jsonify({
            'results': formatted_results,
            'query': query,
            'strategy': strategy,
            'count': len(formatted_results),
            'elapsed_ms': elapsed,
        })
    except Exception as e:
        logger.error(f'Search failed: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/search/by-type', methods=['POST'])
def search_by_type():
    """Search code units by type."""
    if not search_engine:
        return jsonify({'error': 'Workspace not indexed'}), 400

    data = request.get_json()
    unit_type = data.get('type')
    query = data.get('query')
    limit = data.get('limit', 10)

    if not unit_type:
        return jsonify({'error': 'Type required'}), 400

    try:
        results = search_engine.search_by_type(unit_type, query, limit)

        formatted_results = [
            {
                'file': result.unit.file_path,
                'line': result.unit.start_line,
                'name': result.unit.name,
                'type': result.unit.type,
                'signature': result.unit.signature,
                'relevance': result.relevance,
                'docstring': result.unit.docstring,
            }
            for result in results
        ]

        return jsonify({
            'results': formatted_results,
            'count': len(formatted_results),
        })
    except Exception as e:
        logger.error(f'Search by type failed: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/search/by-name', methods=['POST'])
def search_by_name():
    """Search code units by name."""
    if not search_engine:
        return jsonify({'error': 'Workspace not indexed'}), 400

    data = request.get_json()
    name = data.get('name')
    exact = data.get('exact', False)
    limit = data.get('limit', 10)

    if not name:
        return jsonify({'error': 'Name required'}), 400

    try:
        results = search_engine.search_by_name(name, limit, exact)

        formatted_results = [
            {
                'file': result.unit.file_path,
                'line': result.unit.start_line,
                'name': result.unit.name,
                'type': result.unit.type,
                'signature': result.unit.signature,
                'relevance': result.relevance,
                'docstring': result.unit.docstring,
            }
            for result in results
        ]

        return jsonify({
            'results': formatted_results,
            'count': len(formatted_results),
        })
    except Exception as e:
        logger.error(f'Search by name failed: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/dependencies', methods=['POST'])
def find_dependencies():
    """Find dependencies of a code unit."""
    if not search_engine:
        return jsonify({'error': 'Workspace not indexed'}), 400

    data = request.get_json()
    file_path = data.get('file_path')
    unit_name = data.get('unit_name')

    if not file_path or not unit_name:
        return jsonify({'error': 'file_path and unit_name required'}), 400

    try:
        results = search_engine.find_dependencies(file_path, unit_name)

        formatted_results = [
            {
                'file': result.unit.file_path,
                'line': result.unit.start_line,
                'name': result.unit.name,
                'type': result.unit.type,
                'signature': result.unit.signature,
            }
            for result in results
        ]

        return jsonify({
            'results': formatted_results,
            'count': len(formatted_results),
        })
    except Exception as e:
        logger.error(f'Dependency search failed: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/analyze', methods=['GET'])
def analyze():
    """Analyze a file."""
    if not search_engine:
        return jsonify({'error': 'Workspace not indexed'}), 400

    file_path = request.args.get('file')
    if not file_path:
        return jsonify({'error': 'file parameter required'}), 400

    try:
        analysis = search_engine.analyze_file(file_path)
        return jsonify(analysis)
    except Exception as e:
        logger.error(f'File analysis failed: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/statistics', methods=['GET'])
def statistics():
    """Get indexing statistics."""
    if not search_engine:
        return jsonify({'error': 'Workspace not indexed'}), 400

    try:
        stats = search_engine.get_code_statistics()
        return jsonify(stats)
    except Exception as e:
        logger.error(f'Statistics failed: {e}')
        return jsonify({'error': str(e)}), 500


def detect_language(path: str) -> str:
    """Detect programming language from file extensions."""
    path_obj = Path(path)

    # Count file types
    extensions = {}
    for file in path_obj.rglob('*'):
        if file.is_file():
            ext = file.suffix.lower()
            if ext in ['.py']:
                extensions['python'] = extensions.get('python', 0) + 1
            elif ext in ['.js', '.jsx', '.ts', '.tsx']:
                extensions['javascript'] = extensions.get('javascript', 0) + 1
            elif ext in ['.java']:
                extensions['java'] = extensions.get('java', 0) + 1
            elif ext in ['.go']:
                extensions['go'] = extensions.get('go', 0) + 1

    # Return most common language
    if extensions:
        return max(extensions, key=extensions.get)
    return 'python'  # Default


def main():
    parser = argparse.ArgumentParser(description='Semantic Code Search Backend')
    parser.add_argument('--port', type=int, default=5000, help='Port to listen on')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    logger.info(f'Starting Semantic Code Search Backend on {args.host}:{args.port}')
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
