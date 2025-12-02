# AI Script Models - Pydantic schemas for AI-driven editing

from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Optional, Literal, Any

# ============================================================================
# Effect Models
# ============================================================================

class ZoomEffect(BaseModel):
    """Zoom effect configuration"""
    intensity: Literal['subtle', 'medium', 'strong'] = 'medium'
    easing: Literal['linear', 'ease-in', 'ease-out', 'ease-in-out'] = 'ease-in-out'
    duration: float = Field(default=1.0, ge=0.1, le=5.0)

class BlurEffect(BaseModel):
    """Blur effect configuration"""
    type: Literal['background', 'edges'] = 'background'
    intensity: int = Field(default=50, ge=0, le=100)

class HighlightEffects(BaseModel):
    """Effects to apply to a highlight"""
    zoom: Optional[ZoomEffect] = None
    blur: Optional[BlurEffect] = None
    slowMotion: Optional[float] = Field(default=None, ge=0.1, le=1.0)

# ============================================================================
# Timeline Models
# ============================================================================

class JumpCut(BaseModel):
    """Jump cut (segment to remove)"""
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    reason: str
    type: Literal['silence', 'filler', 'mistake', 'pause'] = 'silence'

class Highlight(BaseModel):
    """Highlight (segment to emphasize)"""
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    reason: str
    effects: HighlightEffects = Field(default_factory=HighlightEffects)

class Transition(BaseModel):
    """Transition between scenes"""
    timestamp: float = Field(ge=0)
    type: Literal['cut', 'fade', 'dissolve', 'wipe'] = 'fade'
    duration: float = Field(default=0.5, ge=0.1, le=2.0)

class Timeline(BaseModel):
    """Timeline operations"""
    cuts: List[JumpCut] = Field(default_factory=list)
    highlights: List[Highlight] = Field(default_factory=list)
    transitions: List[Transition] = Field(default_factory=list)

# ============================================================================
# Audio Models
# ============================================================================

class AudioNormalization(BaseModel):
    """Audio normalization settings"""
    enabled: bool = True
    targetLoudness: int = Field(default=-16, ge=-30, le=0)  # LUFS

class AudioSegment(BaseModel):
    """Audio adjustment for specific segment"""
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    action: Literal['boost', 'reduce', 'denoise'] = 'boost'
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)

class BackgroundMusic(BaseModel):
    """Background music settings"""
    enabled: bool = False
    volume: float = Field(default=0.3, ge=0.0, le=1.0)
    duckingIntensity: float = Field(default=0.7, ge=0.0, le=1.0)

class AudioConfig(BaseModel):
    """Audio processing configuration"""
    normalization: AudioNormalization = Field(default_factory=AudioNormalization)
    segments: List[AudioSegment] = Field(default_factory=list)
    backgroundMusic: Optional[BackgroundMusic] = None

# ============================================================================
# Visual Models
# ============================================================================

class ColorGrading(BaseModel):
    """Color grading configuration"""
    preset: Literal['vibrant', 'cinematic', 'natural', 'custom'] = 'vibrant'
    customParams: Optional[Dict[str, float]] = None

class AspectRatio(BaseModel):
    """Aspect ratio conversion settings"""
    target: Literal['9:16', '16:9', '1:1'] = '9:16'
    strategy: Literal['center_crop', 'blur_background', 'letterbox'] = 'center_crop'

class VisualConfig(BaseModel):
    """Visual processing configuration"""
    colorGrading: ColorGrading = Field(default_factory=ColorGrading)
    aspectRatio: AspectRatio = Field(default_factory=AspectRatio)

# ============================================================================
# Subtitle Models
# ============================================================================

class SubtitleSegment(BaseModel):
    """Subtitle segment"""
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str

class SubtitleStyle(BaseModel):
    """Subtitle styling"""
    font: str = 'Kanit ExtraBold'
    size: Literal['auto'] | int = 'auto'
    position: Literal['top', 'center', 'bottom'] = 'bottom'
    color: str = 'white'
    backgroundColor: Optional[str] = None
    outline: bool = True

class SubtitleConfig(BaseModel):
    """Subtitle configuration"""
    segments: List[SubtitleSegment] = Field(default_factory=list)
    style: SubtitleStyle = Field(default_factory=SubtitleStyle)
    keywords: List[str] = Field(default_factory=list)

# ============================================================================
# Metadata Models
# ============================================================================

class ContentMetadata(BaseModel):
    """Content understanding metadata"""
    contentType: Literal['tutorial', 'vlog', 'review', 'entertainment', 'educational'] = 'vlog'
    topic: str = ''
    mood: Literal['energetic', 'calm', 'professional', 'casual'] = 'casual'
    pacing: Literal['fast', 'medium', 'slow'] = 'medium'
    targetAudience: Literal['general', 'professional', 'young'] = 'general'

class Recommendations(BaseModel):
    """AI recommendations"""
    targetDuration: Optional[float] = None
    suggestedThumbnailTimestamp: Optional[float] = None
    qualityScore: int = Field(default=75, ge=0, le=100)
    improvementSuggestions: List[str] = Field(default_factory=list)

# ============================================================================
# Main AI Editing Script
# ============================================================================

class AIEditingScript(BaseModel):
    """Complete AI editing script"""
    job_id: str
    metadata: ContentMetadata = Field(default_factory=ContentMetadata)
    timeline: Timeline = Field(default_factory=Timeline)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    visual: VisualConfig = Field(default_factory=VisualConfig)
    subtitles: SubtitleConfig = Field(default_factory=SubtitleConfig)
    recommendations: Recommendations = Field(default_factory=Recommendations)
    
    @model_validator(mode='before')
    @classmethod
    def convert_old_format(cls, data: Any) -> Any:
        """Convert old frontend format to new structure"""
        if isinstance(data, dict):
            # Convert old subtitles format (array) to new format (object)
            if 'subtitles' in data and isinstance(data['subtitles'], list):
                data['subtitles'] = {
                    'segments': data['subtitles'],
                    'style': {},
                    'keywords': data.get('keywords', [])
                }
            
            # Convert old highlights format if needed
            if 'highlights' in data and isinstance(data['highlights'], list):
                # Wrap in timeline if not already
                if 'timeline' not in data:
                    data['timeline'] = {}
                if isinstance(data['timeline'], dict):
                    # Convert old highlights to new format with effects
                    new_highlights = []
                    for h in data['highlights']:
                        new_highlights.append({
                            'start': h.get('start', 0),
                            'end': h.get('end', 0),
                            'reason': h.get('reason', ''),
                            'effects': {
                                'zoom': {
                                    'intensity': 'medium',
                                    'easing': 'ease-in-out',
                                    'duration': 1.0
                                }
                            }
                        })
                    data['timeline']['highlights'] = new_highlights
                del data['highlights']
            
            # Convert old jumpCuts to timeline.cuts
            if 'jumpCuts' in data and isinstance(data['jumpCuts'], list):
                if 'timeline' not in data:
                    data['timeline'] = {}
                if isinstance(data['timeline'], dict):
                    data['timeline']['cuts'] = [
                        {
                            'start': c.get('start', 0),
                            'end': c.get('end', 0),
                            'reason': c.get('reason', ''),
                            'type': 'silence'
                        }
                        for c in data['jumpCuts']
                    ]
                del data['jumpCuts']
            
            # Set defaults for missing fields
            if 'metadata' not in data:
                data['metadata'] = {}
            
            if 'audio' not in data:
                data['audio'] = {
                    'normalization': {'enabled': True, 'targetLoudness': -16},
                    'segments': []
                }
            
            if 'visual' not in data:
                data['visual'] = {
                    'colorGrading': {'preset': data.get('color_grading', 'vibrant')},
                    'aspectRatio': {'target': '9:16', 'strategy': 'center_crop'}
                }
            
            if 'timeline' not in data:
                data['timeline'] = {}
            
            if 'recommendations' not in data:
                data['recommendations'] = {}
        
        return data
    
    # Helper methods
    def get_zoom_factor(self, intensity: str) -> float:
        """Convert AI intensity to zoom factor"""
        mapping = {
            'subtle': 1.05,
            'medium': 1.15,
            'strong': 1.25
        }
        return mapping.get(intensity, 1.15)
    
    def get_easing_expression(self, easing: str, start: float, end: float, zoom: float) -> str:
        """Generate FFmpeg easing expression"""
        duration = end - start
        
        curves = {
            'linear': f'if(between(t,{start},{end}),{zoom},1)',
            'ease-in': f'if(between(t,{start},{end}),1+({zoom}-1)*pow((t-{start})/{duration},2),1)',
            'ease-out': f'if(between(t,{start},{end}),1+({zoom}-1)*(1-pow(1-(t-{start})/{duration},2)),1)',
            'ease-in-out': f'if(between(t,{start},{end}),if(lt((t-{start})/{duration},0.5),1+({zoom}-1)*2*pow((t-{start})/{duration},2),1+({zoom}-1)*(1-pow(-2*((t-{start})/{duration})+2,2)/2)),1)'
        }
        
        return curves.get(easing, curves['linear'])
