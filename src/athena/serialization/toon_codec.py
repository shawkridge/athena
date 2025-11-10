"""TOON codec wrapper for token-efficient serialization.

Provides encoding/decoding to TOON (Token-Oriented Object Notation) format
for reducing token usage when sending data to LLMs.
"""

import json
import logging
import subprocess
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TOONCodecError(Exception):
    """Base exception for TOON codec errors."""

    pass


class TOONEncodeError(TOONCodecError):
    """Raised when TOON encoding fails."""

    pass


class TOONDecodeError(TOONCodecError):
    """Raised when TOON decoding fails."""

    pass


class TOONCodec:
    """TOON codec for token-efficient serialization.

    Wraps the @toon-format/toon npm package via subprocess,
    providing graceful fallback to JSON if TOON is unavailable.
    """

    _available: Optional[bool] = None
    _encode_time_ms: float = 0.0
    _decode_time_ms: float = 0.0

    @classmethod
    def is_available(cls) -> bool:
        """Check if TOON encoding is available.

        Returns True if @toon-format/toon module is accessible via Node.js.
        Caches result to avoid repeated checks.
        """
        if cls._available is not None:
            return cls._available

        try:
            # Try to load TOON module via Node.js
            result = subprocess.run(
                [
                    "node",
                    "--input-type=module",
                    "-e",
                    "import('/usr/lib/node_modules/@toon-format/toon/dist/index.js').then(m => process.exit(m.encode ? 0 : 1))",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            cls._available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            logger.warning(f"TOON not available: {e}")
            cls._available = False

        return cls._available

    @classmethod
    def encode(cls, data: Dict[str, Any], timeout: int = 10) -> str:
        """Encode data to TOON format.

        Args:
            data: Python dictionary to encode
            timeout: Subprocess timeout in seconds

        Returns:
            TOON-formatted string

        Raises:
            TOONEncodeError: If encoding fails
        """
        if not data:
            return ""

        try:
            start_time = time.time()
            json_data = json.dumps(data)

            # Create Node.js script to encode using TOON module
            node_script = f"""
import('{'/usr/lib/node_modules/@toon-format/toon/dist/index.js'}').then(m => {{
  const data = {json_data};
  const encoded = m.encode(data);
  console.log(encoded);
}}).catch(e => {{
  console.error(e.message);
  process.exit(1);
}});
"""

            result = subprocess.run(
                ["node", "--input-type=module", "-e", node_script],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            cls._encode_time_ms = (time.time() - start_time) * 1000

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"TOON encode failed: {error_msg}")
                raise TOONEncodeError(f"TOON encoding failed: {error_msg}")

            return result.stdout.strip()

        except subprocess.TimeoutExpired as e:
            logger.error(f"TOON encoding timeout after {timeout}s")
            raise TOONEncodeError(f"TOON encoding timeout") from e
        except (FileNotFoundError, OSError) as e:
            logger.error(f"Node.js or TOON not found: {e}")
            raise TOONEncodeError("Node.js or @toon-format/toon not available") from e
        except Exception as e:
            logger.error(f"Unexpected TOON encode error: {e}")
            raise TOONEncodeError(f"Unexpected encoding error: {e}") from e

    @classmethod
    def decode(cls, toon_str: str, timeout: int = 10) -> Dict[str, Any]:
        """Decode TOON format back to JSON.

        Args:
            toon_str: TOON-formatted string
            timeout: Subprocess timeout in seconds

        Returns:
            Decoded Python dictionary

        Raises:
            TOONDecodeError: If decoding fails
        """
        if not toon_str:
            return {}

        try:
            start_time = time.time()

            # Create Node.js script to decode using TOON module
            # Pass TOON data via stdin to avoid escaping issues
            node_script = f"""
import('{'/usr/lib/node_modules/@toon-format/toon/dist/index.js'}').then(m => {{
  let toonStr = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => {{ toonStr += chunk; }});
  process.stdin.on('end', () => {{
    try {{
      const decoded = m.decode(toonStr);
      console.log(JSON.stringify(decoded));
    }} catch (e) {{
      console.error(e.message);
      process.exit(1);
    }}
  }});
}}).catch(e => {{
  console.error(e.message);
  process.exit(1);
}});
"""

            result = subprocess.run(
                ["node", "--input-type=module", "-e", node_script],
                input=toon_str,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            cls._decode_time_ms = (time.time() - start_time) * 1000

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"TOON decode failed: {error_msg}")
                raise TOONDecodeError(f"TOON decoding failed: {error_msg}")

            return json.loads(result.stdout.strip())

        except subprocess.TimeoutExpired as e:
            logger.error(f"TOON decoding timeout after {timeout}s")
            raise TOONDecodeError("TOON decoding timeout") from e
        except (FileNotFoundError, OSError) as e:
            logger.error(f"Node.js or TOON not found: {e}")
            raise TOONDecodeError("Node.js or @toon-format/toon not available") from e
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from TOON decode: {e}")
            raise TOONDecodeError(f"TOON output is not valid JSON: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected TOON decode error: {e}")
            raise TOONDecodeError(f"Unexpected decoding error: {e}") from e

    @classmethod
    def safe_encode(
        cls, data: Dict[str, Any], fallback_to_json: bool = True
    ) -> str:
        """Safely encode to TOON with JSON fallback.

        Args:
            data: Dictionary to encode
            fallback_to_json: If True, returns JSON if TOON fails

        Returns:
            TOON-formatted string or JSON (if fallback enabled)

        Raises:
            TOONEncodeError: If TOON encoding fails and fallback disabled
        """
        try:
            if not cls.is_available():
                if fallback_to_json:
                    logger.debug("TOON unavailable, falling back to JSON")
                    return json.dumps(data)
                raise TOONEncodeError("TOON not available")

            return cls.encode(data)

        except TOONEncodeError as e:
            if fallback_to_json:
                logger.warning(f"TOON encoding failed, using JSON: {e}")
                return json.dumps(data)
            raise

    @classmethod
    def safe_decode(
        cls, data_str: str, fallback_to_json: bool = True
    ) -> Dict[str, Any]:
        """Safely decode from TOON or JSON.

        Attempts TOON decoding first; if that fails, tries JSON parsing.

        Args:
            data_str: String to decode
            fallback_to_json: If True, attempts JSON parsing on TOON failure

        Returns:
            Decoded dictionary

        Raises:
            Exception: If both TOON and JSON decoding fail
        """
        # Try TOON first
        try:
            if cls.is_available():
                return cls.decode(data_str)
        except TOONDecodeError:
            if not fallback_to_json:
                raise

        # Fallback to JSON
        try:
            return json.loads(data_str)
        except json.JSONDecodeError as e:
            logger.error(f"Both TOON and JSON decoding failed: {e}")
            raise

    @classmethod
    def get_last_encode_time_ms(cls) -> float:
        """Get duration of last encode operation in milliseconds."""
        return cls._encode_time_ms

    @classmethod
    def get_last_decode_time_ms(cls) -> float:
        """Get duration of last decode operation in milliseconds."""
        return cls._decode_time_ms

    @classmethod
    def estimate_token_savings(cls, original_json: str, toon_str: str) -> float:
        """Estimate token reduction percentage.

        Args:
            original_json: Original JSON string
            toon_str: TOON-encoded string

        Returns:
            Percentage token reduction (0-100)
        """
        if not original_json:
            return 0.0

        # Rough approximation: tokens ≈ chars / 4 (average token size)
        original_tokens = len(original_json) / 4
        toon_tokens = len(toon_str) / 4

        if original_tokens == 0:
            return 0.0

        return ((original_tokens - toon_tokens) / original_tokens) * 100
