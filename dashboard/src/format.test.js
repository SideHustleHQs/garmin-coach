import { describe, it, expect } from 'vitest'
import { paceStr, durationStr, kmStr, sleepStr } from './format'

describe('format', () => {
  it('paceStr formats s/km as m:ss', () => {
    expect(paceStr(312)).toBe('5:12')
    expect(paceStr(300)).toBe('5:00')
    expect(paceStr(null)).toBe('–')
  })
  it('durationStr formats seconds as h:mm:ss or m:ss', () => {
    expect(durationStr(2558)).toBe('42:38')
    expect(durationStr(4700)).toBe('1:18:20')
    expect(durationStr(null)).toBe('–')
  })
  it('kmStr uses comma decimal', () => {
    expect(kmStr(8.2)).toBe('8,2')
    expect(kmStr(null)).toBe('–')
  })
  it('sleepStr formats seconds as h:mm', () => {
    expect(sleepStr(27720)).toBe('7:42')
    expect(sleepStr(null)).toBe('–')
  })
})
