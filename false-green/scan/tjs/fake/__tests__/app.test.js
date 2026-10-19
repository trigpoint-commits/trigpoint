describe.only('focused block', () => {
  it('adds', () => { expect(1 + 1).toBe(2); });
});
it('empty test', () => {});
it('tautology', () => { const x = compute(); expect(true).toBe(true); });
it('no assertion', () => { const u = makeUser('bob'); render(u); });
it.skip('later', () => { expect(add(2,2)).toBe(5); });
