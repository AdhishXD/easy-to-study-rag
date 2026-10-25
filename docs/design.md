# Interface design

The interface applies the [Apple design skill supplied for this project](https://github.com/emilkowalski/skills/blob/main/skills/apple-design/SKILL.md).

- Purpose: keep the course, its evidence, and practice close together.
- Typography: system fonts, tighter heading tracking, comfortable body line height, and sizes in rem.
- Color: neutral white and slate surfaces with one subdued blue accent. Feedback uses restrained green/red.
- Hierarchy: persistent subject navigation, four explicit course sections, and deeper details in focused dialogs.
- Response: immediate pressed states, interruptible spring movement on the section control, and visible background job progress.
- Materials: subtle translucency only in navigation and dialog headers, with solid content for readability.
- Agency: cancel processing, inspect source text, correct exam years, and review removal before committing it.
- Accessibility: semantic controls, keyboard focus, native dialog focus containment, a skip link, reduced motion/transparency, and contrast preferences.
- Responsive layout: desktop sidebar becomes a mobile drawer; course content remains available without horizontal overflow.

The source reader loads one page at a time and the topic list starts with twenty rows. This reduces rendering work while keeping search and deeper exploration available. Source labels describe supplied evidence; they are not a guarantee that every generated sentence is correct.
