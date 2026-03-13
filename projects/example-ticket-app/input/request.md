# Raw Stakeholder Input — Example

> This file represents what a product manager or stakeholder might drop into
> the pipeline. It's deliberately unstructured to show what the Requirements
> Agent has to work with.

---

We need a way for customers to submit support tickets through our website and
track the status of their requests. The support team needs to be able to view
all tickets, assign them to agents, update status, and add internal notes that
customers can't see. Customers should get email notifications when their ticket
status changes.

It needs to be fast and handle a few thousand tickets per day. We want to make
sure we can search tickets by keyword, filter by status and date, and export
to CSV for reporting.

Oh also, our CEO wants a dashboard showing ticket volume, average resolution
time, and agent performance. Maybe built in React? And we were thinking Node.js
for the backend since our frontend team knows it.

It needs to connect to our existing customer database (Postgres) and we use
Azure Communication Services for emails.

We want this done in 6 weeks.
