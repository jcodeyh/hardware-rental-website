import { Inbox } from '@novu/react';

export default function NotificationBell({ userId }) {
  const applicationIdentifier =
    import.meta.env.VITE_NOVU_APP_IDENTIFIER || 'OKvqutCb0f1f';

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