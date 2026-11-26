import { Inbox } from '@novu/react';

export default function NotificationBell({ userId }) {
  const applicationIdentifier =
    import.meta.env.VITE_NOVU_APP_IDENTIFIER || 'w7tJlfaANocl';

  const subscriberId = String(userId || 'local-preview-user');

  return (
    <Inbox
      applicationIdentifier={applicationIdentifier}
      subscriber={{
        subscriberId,
      }}
    />
  );
}