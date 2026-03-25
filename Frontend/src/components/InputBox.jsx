import { useEffect, useEffectEvent, useRef, useState } from 'react'

function MicIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5 fill-current">
      <path d="M12 15a3 3 0 0 0 3-3V7a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Zm5-3a1 1 0 1 1 2 0 7 7 0 0 1-6 6.93V21h3a1 1 0 1 1 0 2H8a1 1 0 1 1 0-2h3v-2.07A7 7 0 0 1 5 12a1 1 0 1 1 2 0 5 5 0 1 0 10 0Z" />
    </svg>
  )
}

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
      <div className="mx-auto flex max-w-3xl flex-col gap-2 rounded-[28px] border border-white/10 bg-[#2a2a2a] p-3">
        <div className="flex items-end gap-3">
          <button
            type="button"
            onClick={handleMicClick}
            disabled={isTyping}
            className={`hidden h-11 w-11 shrink-0 items-center justify-center rounded-full border text-zinc-200 transition sm:inline-flex ${
              isListening
                ? 'border-white/20 bg-[#3a3a3a]'
                : 'border-white/10 bg-[#212121] hover:bg-[#303030]'
            } disabled:cursor-not-allowed disabled:opacity-50`}
            aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
            title={
              isMicSupported
                ? isListening
                  ? 'Stop voice input'
                  : 'Start voice input'
                : 'Voice input is not supported in this browser'
            }
          >
            <MicIcon />
          </button>

          <textarea
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="Message FindX"
            className="max-h-40 min-h-[44px] flex-1 resize-none bg-transparent px-1 py-2 text-sm text-white outline-none placeholder:text-zinc-500"
          />

          <button
            type="button"
            onClick={() => onSubmit(input)}
            disabled={isTyping || !input.trim()}
            className="inline-flex h-11 shrink-0 items-center justify-center rounded-full bg-white px-4 text-sm font-medium text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:bg-zinc-600"
          >
            Send
          </button>
        </div>

        {micError ? <p className="px-1 text-xs text-red-300">{micError}</p> : null}
      </div>
    </div>
  )
}

export default InputBox
