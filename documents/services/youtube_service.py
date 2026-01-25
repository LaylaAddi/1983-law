"""
YouTube transcript extraction service using Supadata API.
For Monthly and Annual Pro subscribers only.
"""
import re
import requests
import logging
from typing import Optional
from dataclasses import dataclass

from django.conf import settings


logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    """Information about a YouTube video."""
    video_id: str
    title: str
    duration_seconds: Optional[int]
    has_captions: bool
    available_languages: list


@dataclass
class TranscriptSegment:
    """A single segment of transcript with timing."""
    text: str
    start_ms: int  # Offset in milliseconds
    duration_ms: int

    @property
    def start_seconds(self) -> float:
        return self.start_ms / 1000

    @property
    def end_seconds(self) -> float:
        return (self.start_ms + self.duration_ms) / 1000

    @property
    def start_display(self) -> str:
        """Format as MM:SS or HH:MM:SS."""
        return self._seconds_to_display(self.start_seconds)

    @staticmethod
    def _seconds_to_display(seconds: float) -> str:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"


@dataclass
class TranscriptResult:
    """Result of transcript extraction."""
    success: bool
    segments: list  # List of TranscriptSegment
    full_text: str
    language: str
    extraction_method: str  # 'youtube' or 'whisper'
    error: Optional[str] = None


class YouTubeServiceError(Exception):
    """Custom exception for YouTube service errors."""
    pass


class YouTubeService:
    """
    Service for extracting transcripts from YouTube videos.
    Uses Supadata API for reliable extraction.
    """

    BASE_URL = "https://api.supadata.ai/v1"
    MAX_CLIP_SECONDS = 120  # 2 minutes max per clip

    def __init__(self):
        self.api_key = settings.SUPADATA_API_KEY
        if not self.api_key:
            raise ValueError("SUPADATA_API_KEY not configured in settings")

    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    @staticmethod
    def extract_video_id(url: str) -> str:
        """
        Extract YouTube video ID from various URL formats.

        Supports:
        - youtube.com/watch?v=VIDEO_ID
        - youtu.be/VIDEO_ID
        - youtube.com/embed/VIDEO_ID
        - youtube.com/v/VIDEO_ID
        """
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
            r'(?:youtube\.com\/watch\?.*v=)([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return ''

    @staticmethod
    def build_youtube_url(video_id: str) -> str:
        """Build a standard YouTube URL from video ID."""
        return f"https://www.youtube.com/watch?v={video_id}"

    def get_transcript(
        self,
        youtube_url: str,
        language: str = "en",
        use_ai_fallback: bool = True
    ) -> TranscriptResult:
        """
        Fetch full transcript for a YouTube video.

        Args:
            youtube_url: Full YouTube URL or video ID
            language: Preferred language code (ISO 639-1)
            use_ai_fallback: If True, use AI transcription when no captions exist

        Returns:
            TranscriptResult with segments and metadata
        """
        # Ensure we have a full URL
        if not youtube_url.startswith('http'):
            youtube_url = self.build_youtube_url(youtube_url)

        # Try native captions first (free/cheap)
        result = self._fetch_transcript(youtube_url, language, mode="native")

        if result.success:
            return result

        # Fall back to AI transcription if enabled
        if use_ai_fallback:
            logger.info(f"No native captions, falling back to AI transcription for {youtube_url}")
            result = self._fetch_transcript(youtube_url, language, mode="generate")
            if result.success:
                result.extraction_method = "whisper"
                return result

        return result

    def _fetch_transcript(
        self,
        youtube_url: str,
        language: str,
        mode: str = "native"
    ) -> TranscriptResult:
        """
        Internal method to fetch transcript from Supadata API.

        Args:
            youtube_url: Full YouTube URL
            language: Preferred language code
            mode: 'native' for existing captions, 'generate' for AI transcription
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/transcript",
                headers=self._get_headers(),
                params={
                    "url": youtube_url,
                    "lang": language,
                    "mode": mode,
                },
                timeout=60  # Generous timeout for AI transcription
            )

            if response.status_code == 404:
                return TranscriptResult(
                    success=False,
                    segments=[],
                    full_text="",
                    language="",
                    extraction_method=mode,
                    error="No transcript available for this video"
                )

            if response.status_code == 429:
                return TranscriptResult(
                    success=False,
                    segments=[],
                    full_text="",
                    language="",
                    extraction_method=mode,
                    error="Rate limit exceeded. Please try again in a moment."
                )

            if response.status_code != 200:
                logger.error(f"Supadata API error: {response.status_code} - {response.text}")
                return TranscriptResult(
                    success=False,
                    segments=[],
                    full_text="",
                    language="",
                    extraction_method=mode,
                    error=f"API error: {response.status_code}"
                )

            data = response.json()

            # Check for async job (large videos)
            if "jobId" in data:
                return self._poll_job(data["jobId"], mode)

            # Parse segments from response
            segments = []
            content = data.get("content", [])

            for item in content:
                segment = TranscriptSegment(
                    text=item.get("text", ""),
                    start_ms=item.get("offset", 0),
                    duration_ms=item.get("duration", 0)
                )
                segments.append(segment)

            # Build full text
            full_text = " ".join(s.text for s in segments)

            return TranscriptResult(
                success=True,
                segments=segments,
                full_text=full_text,
                language=data.get("lang", language),
                extraction_method="youtube" if mode == "native" else "whisper"
            )

        except requests.exceptions.Timeout:
            return TranscriptResult(
                success=False,
                segments=[],
                full_text="",
                language="",
                extraction_method=mode,
                error="Request timed out. Please try again."
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching transcript: {e}")
            return TranscriptResult(
                success=False,
                segments=[],
                full_text="",
                language="",
                extraction_method=mode,
                error=f"Network error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error fetching transcript: {e}")
            return TranscriptResult(
                success=False,
                segments=[],
                full_text="",
                language="",
                extraction_method=mode,
                error=str(e)
            )

    def _poll_job(self, job_id: str, mode: str, max_attempts: int = 30) -> TranscriptResult:
        """
        Poll for async job completion.

        Args:
            job_id: The job ID returned by initial request
            mode: Extraction mode for result
            max_attempts: Maximum polling attempts (default 30 = ~60 seconds)
        """
        import time

        for attempt in range(max_attempts):
            try:
                response = requests.get(
                    f"{self.BASE_URL}/transcript/{job_id}",
                    headers=self._get_headers(),
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()

                    # Check if still processing
                    if data.get("status") == "processing":
                        time.sleep(2)
                        continue

                    # Parse completed result
                    segments = []
                    content = data.get("content", [])

                    for item in content:
                        segment = TranscriptSegment(
                            text=item.get("text", ""),
                            start_ms=item.get("offset", 0),
                            duration_ms=item.get("duration", 0)
                        )
                        segments.append(segment)

                    full_text = " ".join(s.text for s in segments)

                    return TranscriptResult(
                        success=True,
                        segments=segments,
                        full_text=full_text,
                        language=data.get("lang", "en"),
                        extraction_method="youtube" if mode == "native" else "whisper"
                    )

                elif response.status_code == 404:
                    # Job not ready yet
                    time.sleep(2)
                    continue
                else:
                    return TranscriptResult(
                        success=False,
                        segments=[],
                        full_text="",
                        language="",
                        extraction_method=mode,
                        error=f"Job polling failed: {response.status_code}"
                    )

            except Exception as e:
                logger.error(f"Error polling job {job_id}: {e}")
                time.sleep(2)
                continue

        return TranscriptResult(
            success=False,
            segments=[],
            full_text="",
            language="",
            extraction_method=mode,
            error="Transcript extraction timed out"
        )

    def get_transcript_for_range(
        self,
        youtube_url: str,
        start_seconds: int,
        end_seconds: int,
        language: str = "en",
        use_ai_fallback: bool = True
    ) -> TranscriptResult:
        """
        Get transcript for a specific time range (clip).

        Args:
            youtube_url: Full YouTube URL or video ID
            start_seconds: Start time in seconds
            end_seconds: End time in seconds
            language: Preferred language code
            use_ai_fallback: Use AI if no captions

        Returns:
            TranscriptResult with only segments in the specified range

        Raises:
            ValueError: If clip exceeds 2 minute limit
        """
        # Validate clip length
        duration = end_seconds - start_seconds
        if duration > self.MAX_CLIP_SECONDS:
            raise ValueError(f"Clip duration ({duration}s) exceeds maximum of {self.MAX_CLIP_SECONDS}s (2 minutes)")

        if duration <= 0:
            raise ValueError("End time must be after start time")

        # Get full transcript
        result = self.get_transcript(youtube_url, language, use_ai_fallback)

        if not result.success:
            return result

        # Filter segments to time range
        # Include segments that overlap with the range
        start_ms = start_seconds * 1000
        end_ms = end_seconds * 1000

        filtered_segments = []
        for segment in result.segments:
            segment_start = segment.start_ms
            segment_end = segment.start_ms + segment.duration_ms

            # Check if segment overlaps with our range
            if segment_end >= start_ms and segment_start <= end_ms:
                filtered_segments.append(segment)

        # Rebuild full text from filtered segments
        filtered_text = " ".join(s.text for s in filtered_segments)

        return TranscriptResult(
            success=True,
            segments=filtered_segments,
            full_text=filtered_text,
            language=result.language,
            extraction_method=result.extraction_method
        )

    def check_captions_available(self, youtube_url: str) -> tuple[bool, list]:
        """
        Check if captions are available for a video without fetching full transcript.

        Returns:
            Tuple of (has_captions, available_languages)
        """
        # For now, we try to fetch with native mode and check result
        # A more efficient approach would be to use YouTube Data API
        # but that requires separate API key and quota
        result = self._fetch_transcript(youtube_url, "en", mode="native")

        if result.success:
            return True, [result.language]

        return False, []


# Convenience function for simple usage
def get_youtube_transcript(url: str, start: int = None, end: int = None) -> TranscriptResult:
    """
    Convenience function to get YouTube transcript.

    Args:
        url: YouTube URL
        start: Optional start time in seconds
        end: Optional end time in seconds

    Returns:
        TranscriptResult
    """
    service = YouTubeService()

    if start is not None and end is not None:
        return service.get_transcript_for_range(url, start, end)

    return service.get_transcript(url)
