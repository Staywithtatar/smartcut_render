# AI Service Configuration Guide

## Overview
AutoCut Influencer supports multiple AI services for video transcription and analysis with automatic fallback.

## Supported Services

### 1. Google AI (Gemini) - **Recommended**
- **Cost**: Free tier available
- **Limits**: 50MB video size, 60 requests/minute
- **Quality**: Excellent for Thai language
- **Setup**: Get API key from https://makersuite.google.com/app/apikey

### 2. OpenAI Whisper
- **Cost**: $0.006/minute (~6 สตางค์/นาที)
- **Limits**: 25MB file size
- **Quality**: Excellent multilingual support
- **Setup**: Get API key from https://platform.openai.com/api-keys

## Configuration

### Environment Variables

Add to `webfront/.env.local`:

```env
# Google AI (Primary - Free)
GOOGLE_AI_API_KEY=your_google_ai_key_here

# OpenAI (Fallback - Paid)
OPENAI_API_KEY=your_openai_key_here

# Python Worker
PYTHON_WORKER_URL=http://localhost:8000

# Supabase
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

## Service Priority

The system automatically tries services in this order:

1. **Google AI** (if `GOOGLE_AI_API_KEY` is set)
   - Free tier
   - Best for Thai language
   - 50MB limit

2. **Whisper** (if `OPENAI_API_KEY` is set)
   - Paid service
   - Fallback if Google AI fails
   - 25MB limit

## Error Handling

### Automatic Fallback
If Google AI fails, the system automatically falls back to Whisper:

```
🤖 Attempting transcription with Google AI...
❌ Google AI failed: Video too large
🎙️ Attempting transcription with Whisper...
✅ Whisper transcribed: 45 segments
```

### No API Keys
If no API keys are configured:

```json
{
  "error": "No AI service configured. Please set GOOGLE_AI_API_KEY or OPENAI_API_KEY"
}
```

## Best Practices

### For Development
Use Google AI (free):
```env
GOOGLE_AI_API_KEY=your_key
```

### For Production
Use both for redundancy:
```env
GOOGLE_AI_API_KEY=your_google_key
OPENAI_API_KEY=your_openai_key
```

### File Size Limits
- Videos > 50MB: Use Whisper only
- Videos < 25MB: Both services work
- Videos 25-50MB: Google AI only

## Cost Optimization

### Free Tier (Google AI)
- 60 requests/minute
- 1,500 requests/day
- Perfect for development and small-scale production

### Paid Tier (Whisper)
- $0.006/minute of audio
- Example: 30-second video = ~$0.003 (3 สตางค์)
- Use as fallback only

## Monitoring

Check which service was used in logs:

```
🔑 Available AI services: google-ai, whisper
🤖 Attempting transcription with Google AI...
✅ Google AI transcribed: 45 segments
```

## Troubleshooting

### Google AI Errors
- **Video too large**: Reduce video size or use Whisper
- **Rate limit**: Wait 1 minute or use Whisper
- **Invalid API key**: Check key at https://makersuite.google.com

### Whisper Errors
- **File too large**: Compress video to < 25MB
- **Insufficient quota**: Add credits to OpenAI account
- **Invalid API key**: Check key at https://platform.openai.com

## Testing

Test transcription with curl:

```bash
curl -X POST http://localhost:3000/api/jobs/process \
  -H "Content-Type: application/json" \
  -d '{"jobId": "your-job-id"}'
```

Check response for `servicesUsed`:

```json
{
  "success": true,
  "jobId": "...",
  "servicesUsed": ["google-ai"]
}
```
