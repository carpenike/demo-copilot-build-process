# Raw Stakeholder Input — Expense Portal

> This file represents what a stakeholder might drop into the pipeline as an
> informal request. Compare with `business-requirements.md` in this same folder
> for the formal BRD version. Both are valid inputs to @1-requirements.

---

Hey team — Finance is killing us with the current expense process. Everything
is paper forms, email chains for approvals, and then someone in accounting
manually types it all into SAP. It takes like two weeks to get reimbursed and
half the time receipts get lost.

We need a web app where employees can submit expenses, snap a photo of their
receipt, and have it go through the approval chain automatically. Managers
approve, then Finance does a final review for anything over $500. The usual
stuff — per diem limits, no duplicate submissions, policy checks.

It needs to pull employee/manager data from Workday and push approved expenses
to SAP for payment. We want email notifications when things get submitted,
approved, or rejected.

Finance wants dashboards showing spend by cost center and category. Managers
want to see what's pending and how their team's spending tracks against budget.
Oh and we need an admin panel so Finance can tweak policy rules without asking
engineering every time.

Don't worry about corporate credit cards or travel booking — those are separate
projects. And we don't need a native mobile app, just make sure the web version
works on phones for the receipt photo thing.

Some people mentioned using React for the frontend and maybe a Node.js backend
since the intern knows JavaScript. We're flexible on that though.

We're hoping to be live by end of Q3. Let us know what you think is realistic.
