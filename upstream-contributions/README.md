# Upstream Contributions — Mainline Linux

Accepted patches submitted upstream via `git send-email` and the kernel mailing
lists. Kernel patches are never merged through GitHub pull requests, so this
directory mirrors them here for discoverability and permanent archival.

## Submitted

| Patch | Subsystem | Tracker | State |
|:---|:---|:---|:---|
| [media: cx25840: return -EOPNOTSUPP instead of WARN_ON in cx25840_init](0001-media-cx25840-return-EOPNOTSUPP-instead-of-WARN_ON.patch) | `drivers/media/i2c/cx25840` | [linux-media #158059](http://patchwork.linuxtv.org/project/linux-media/patch/CACaF87XKQbdLEHTCLFZh=TAt__dZzWf_d1vneKU9Lnx8kAHEiA@mail.gmail.com/) | Accepted (delegate: Hans Verkuil), queued for the media tree |

### How this was found

Reported by `syzbot` (the kernel's automated fuzzing infrastructure) as report
`9123948aef13fe92d706`. `cx25840_init()` calls `WARN_ON(1)` on unsupported chip
variants, which trips kernel warnings and syzbot alerts on hardware the driver
does not fully support. The fix returns `-EOPNOTSUPP` early so callers such as
`cxusb_medion_register_analog_subdevs()` can handle the failure cleanly
instead of the driver silently reporting success while leaving the chip
unconfigured.

### Reapplying

```bash
git am 0001-media-cx25840-return-EOPNOTSUPP-instead-of-WARN_ON.patch
```

The mbox headers are preserved, so the `Message-ID`, `From`, and
`Signed-off-by` fields all remain intact for `b4`-based tooling:

```bash
b4 am -T 0001-media-cx25840-return-EOPNOTSUPP-instead-of-WARN_ON.patch
```
