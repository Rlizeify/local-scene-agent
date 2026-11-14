# Profile updates

Taste, address and rules change. The profile is versioned with a changelog and re-approval.

1. **Understand the change.** "I'm into jazz now", "I moved to the east side", "no more late nights", "I sold my car".
2. **Find every field it touches.** Moving changes `home.areas` minutes, maybe `max_drive_minutes`, `sources` and `venues[].area`. A new interest needs keywords, a weight (where does it rank?), rooms and at least one source.
3. **Show the exact YAML diff** and confirm.
4. **Apply it**, then:
   ```
   lsa profile touch --change '<one line>'
   lsa profile validate
   lsa profile summary   # show the changed sections
   ```
   `touch` drops the profile back to draft.
5. **Re-approve** only on their explicit yes: `lsa profile approve`.
6. **Cloud routine?** Re-render it (`lsa schedule render ... --target cloud`) and offer to update the routine.

The skill itself never needs regenerating for profile edits; it reads the live profile.
