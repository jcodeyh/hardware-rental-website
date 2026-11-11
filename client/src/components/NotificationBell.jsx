import { Inbox } from '@novu/react';

export default function NotificationBell({ userId }) {
  return (
    <Inbox
      applicationIdentifier="w7tJlfaANocl"
      subscriber={{
        subscriberId: String(userId || 'local-preview-user'),
      }}
    />
  );
}