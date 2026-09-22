import type { ReactNode } from 'react';

export function LearnerHeader({ subtitle, children }: { subtitle: string; children?: ReactNode }) {
  return <header className="learner-header">
    <div className="learner-brand">
      <span className="learner-brand-mark" aria-hidden="true">L</span>
      <span><strong>Luna</strong><small>{subtitle}</small></span>
    </div>
    <div className="learner-header-actions">{children}</div>
  </header>;
}
