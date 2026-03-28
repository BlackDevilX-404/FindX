/**
 * System identifier utility for tracking which system is accessing the application.
 * Uses a combination of browser and system information to create a unique identifier.
 */

/**
 * Generate a unique system identifier for the client.
 * Uses localStorage to persist the ID across sessions.
 * Falls back to generating one based on browser/platform info if not found.
 *
 * @returns {string} A unique system identifier
 */
export function getSystemId() {
  const STORAGE_KEY = 'findx-system-id'
  
  // Try to retrieve stored system ID
  let systemId = window.localStorage.getItem(STORAGE_KEY)
  
  if (!systemId) {
    // Generate a new system ID based on browser info
    systemId = generateSystemId()
    
    // Store it for future use
    try {
      window.localStorage.setItem(STORAGE_KEY, systemId)
    } catch (e) {
      // If localStorage is not available, just use the generated ID
      console.warn('Could not store system ID in localStorage:', e)
    }
  }
  
  return systemId
}

/**
 * Generate a system ID based on browser and platform information.
 *
 * @returns {string} Generated system identifier
 */
function generateSystemId() {
  const userAgent = window.navigator.userAgent
  const platform = window.navigator.platform
  const language = window.navigator.language
  const screenResolution = `${window.screen.width}x${window.screen.height}`
  
  // Create a combination of identifiers
  const identifier = `${platform}-${language}-${screenResolution}`
  
  // Create a simple hash from the identifier
  let hash = 0
  for (let i = 0; i < identifier.length; i++) {
    const char = identifier.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash // Convert to 32bit integer
  }
  
  // Use hostname if available via WebRTC (advanced), otherwise use generated hash
  const systemName = `system-${Math.abs(hash).toString(16)}`
  
  return systemName
}

/**
 * Get system information for debugging purposes.
 *
 * @returns {object} System information
 */
export function getSystemInfo() {
  return {
    systemId: getSystemId(),
    platform: window.navigator.platform,
    userAgent: window.navigator.userAgent,
    language: window.navigator.language,
    screenResolution: `${window.screen.width}x${window.screen.height}`,
    timestamp: new Date().toISOString(),
  }
}
