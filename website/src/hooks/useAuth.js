import { useState, useEffect, useCallback } from 'react'
import { AuthClient } from '@dfinity/auth-client'

let authClient = null

async function getClient() {
  if (!authClient) {
    authClient = await AuthClient.create()
  }
  return authClient
}

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [principal, setPrincipal] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    async function check() {
      try {
        const client = await getClient()
        const authenticated = await client.isAuthenticated()
        if (mounted) {
          setIsAuthenticated(authenticated)
          if (authenticated) {
            const identity = client.getIdentity()
            setPrincipal(identity.getPrincipal().toText())
          }
        }
      } catch (e) {
        console.error('Auth check failed:', e)
      } finally {
        if (mounted) setIsLoading(false)
      }
    }
    check()
    return () => { mounted = false }
  }, [])

  const login = useCallback(async () => {
    setIsLoading(true)
    try {
      const client = await getClient()
      await client.login({
        identityProvider: 'https://identity.ic0.app',
        onSuccess: () => {
          const identity = client.getIdentity()
          setIsAuthenticated(true)
          setPrincipal(identity.getPrincipal().toText())
          setIsLoading(false)
        },
        onError: (err) => {
          console.error('Login failed:', err)
          setIsLoading(false)
        },
      })
    } catch (e) {
      console.error('Login error:', e)
      setIsLoading(false)
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      const client = await getClient()
      await client.logout()
      setIsAuthenticated(false)
      setPrincipal(null)
    } catch (e) {
      console.error('Logout error:', e)
    }
  }, [])

  return { isAuthenticated, principal, isLoading, login, logout }
}
