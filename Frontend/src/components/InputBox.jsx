import { useEffect, useEffectEvent, useRef, useState } from 'react'

function InputBox({ input, onInputChange, onSubmit, isTyping }) {
  const recognitionRef = useRef(null)
  const [isMicSupported, setIsMicSupported] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [micError, setMicError] = useState('')

  const handleTranscript = useEffectEvent((transcript) => {
    const nextValue = input.trim() ? `${input.trim()} ${transcript}` : transcript
    onInputChange(nextValue)
  })

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition

    if (!SpeechRecognition) {
      setIsMicSupported(false)
      return
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-US'

    recognition.onstart = () => {
      setMicError('')
      setIsListening(true)
    }

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript ?? '')
        .join(' ')
        .trim()

      if (transcript) {
        handleTranscript(transcript)
      }
    }

    recognition.onerror = (event) => {
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        setMicError('Microphone permission was blocked in the browser.')
      } else if (event.error === 'no-speech') {
        setMicError('No speech was detected. Try again.')
      } else {
        setMicError('Voice input failed. Try again.')
      }
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    recognitionRef.current = recognition
    setIsMicSupported(true)

    return () => {
      recognition.stop()
      recognitionRef.current = null
    }
  }, [handleTranscript])

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      onSubmit(input)
    }
  }

  const handleMicClick = () => {
    if (!recognitionRef.current || !isMicSupported) {
      setMicError('Voice input is not supported in this browser.')
      return
    }

    if (isListening) {
      recognitionRef.current.stop()
      return
    }

    setMicError('')
    recognitionRef.current.start()
  }

  return (
    <div className="border-t border-white/10 px-4 py-4">
      <div className="rounded-[26px] border border-white/10 bg-slate-950/60 p-3 shadow-inner shadow-slate-950/30">
        <div className="flex items-end gap-3">
          <button
            type="button"
            onClick={handleMicClick}
            disabled={isTyping}
            className={`hidden h-11 w-11 shrink-0 items-center justify-center rounded-2xl border text-sm transition sm:inline-flex ${
              isListening
                ? 'border-blue-300/40 bg-blue-500/15 text-blue-100'
                : 'border-white/10 bg-white/5 text-slate-300 hover:bg-white/10'
            } disabled:cursor-not-allowed disabled:opacity-50`}
            aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
            aria-pressed={isListening}
            title={
              isMicSupported
                ? isListening
                  ? 'Stop voice input'
                  : 'Start voice input'
                : 'Voice input is not supported in this browser'
            }
          >
            {isListening ? 'Rec' : 'Mic'}
          </button>

          <div className="flex-1">
            <textarea
              value={input}
              onChange={(event) => onInputChange(event.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              placeholder="Ask about HR policy, compliance, leave, onboarding, or company knowledge..."
              className="max-h-36 min-h-[44px] w-full resize-none bg-transparent px-2 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-500"
            />

            <div className="mt-1 px-2 text-[11px] text-slate-500">
              {micError
                ? micError
                : isListening
                  ? 'Listening... speak now.'
                  : isMicSupported
                    ? 'Click Mic to dictate.'
                    : 'Voice input is available only in supported browsers.'}
            </div>
          </div>

          <button
            type="button"
            onClick={() => onSubmit(input)}
            disabled={isTyping || !input.trim()}
            className="inline-flex h-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-r from-blue-500 to-indigo-500 px-4 text-sm font-medium text-white shadow-lg shadow-blue-950/30 transition hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}

export default InputBox
