export function NewSessionButton({ busy, onClick }: { busy: boolean; onClick(): void }) {
  return <button className="secondary-button" disabled={busy} onClick={onClick}>New session</button>;
}
