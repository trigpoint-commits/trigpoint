import { expect, it } from 'vitest';
it('adds', () => { expect(add(2,2)).toBe(4); });
it('throws on empty', () => { expect(() => parse('')).toThrow(); });
it('smoke', () => { const s = new Server(); s.start(); expect(s.running).toBe(true); });
