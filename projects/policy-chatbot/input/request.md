# Raw Stakeholder Input — Policy Chatbot

> This file represents what a stakeholder might drop into the pipeline as an
> informal request. Compare with `business-requirements.md` in this same folder
> for the formal BRD version. Both are valid inputs to @1-requirements.

---

So we have this huge problem — HR gets hundreds of tickets every week from
people asking basic policy questions. "What's the bereavement leave policy?"
"How do I get a parking badge?" "Where do I report a safety issue?" All of
this stuff is already documented, but nobody can find it because the policies
are scattered across SharePoint, the intranet, and random PDF files.

We want to build a chatbot that employees can ask questions and get actual
answers pulled from our policy documents. Not made-up answers — it has to cite
the exact policy and section. If the chatbot doesn't know, it should say so and
hand off to a real person.

The cool part: we want it to not just answer the question but give you a
checklist of what to do next. Like if someone asks about parental leave, it
should tell them the policy AND give them steps — "1. Notify your manager,
2. Submit the form in Workday, 3. Contact Benefits at this email." And where
possible, it should link directly to the systems they need (Workday, ServiceNow,
the facilities booking system, etc.).

It needs to work in Microsoft Teams since that's where everyone lives, and also
as a widget on the intranet for people who prefer the browser.

We've got about 140 policy documents across HR, IT, Finance, Facilities, Legal,
Compliance, and Safety. The chatbot needs to ingest all of them and stay
up-to-date when policies change.

Oh and we need an admin panel so the policy team can upload new docs, re-index,
and test how the chatbot answers questions. Plus analytics — what are people
asking about, what's the chatbot getting wrong, where are people escalating.

Someone on the team suggested we could use ChatGPT's API directly or maybe
build this in Node.js since there are good chatbot frameworks. We're open to
suggestions on the tech stack though.

We'd love to have the top 50 most common policy questions working by launch,
and then expand from there.
