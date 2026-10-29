# Interface design

The interface is guided by Apple's official [UI design principles](https://developer.apple.com/design/tips/) and [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/), together with the public [Frontend Design skill](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md) and [Apple Design skill](https://github.com/bowen31337/apple-design/blob/main/SKILL.md). These are references for clarity and craft, not a license to copy Apple branding.

- Purpose: keep the course, its evidence, and practice close together.
- Typography: system fonts, tighter heading tracking, comfortable body line height, and sizes in rem.
- Color: adaptive-looking white and soft-gray surfaces with one familiar blue action color. Feedback uses restrained green/red.
- Hierarchy: persistent subject navigation, four explicit course sections, and deeper details in focused dialogs.
- Response: immediate pressed states, interruptible spring movement on the section control, and visible background job progress.
- Materials: subtle translucency only in navigation and dialog headers, with solid content for readability.
- Agency: cancel processing, inspect source text, correct exam years, and review removal before committing it.
- Accessibility: semantic controls, keyboard focus, native dialog focus containment, a skip link, reduced motion/transparency, and contrast preferences.
- Responsive layout: desktop sidebar becomes a mobile drawer; course content remains available without horizontal overflow.
- Daily use: the most common loop stays shallow—open a subject, see the study plan, continue practice, and open the exact supporting page.
- Citations: source links use stable filename-and-page identities and human-readable labels; UI indexes and backend citation syntax are never shown.

The source reader loads one page at a time and the topic list starts with twenty rows. This reduces rendering work while keeping search and deeper exploration available. Source labels describe supplied evidence; they are not a guarantee that every generated sentence is correct.
