# Idle Pattern Discovery Report

- Machines processed: 5
- Idle windows detected: 140
- Active windows sampled: 86
- Idle plots generated: 5

## Idle Pattern Distribution

- frozen: 132 windows
- constant_low_variance: 5 windows
- low_activity: 3 windows

## Idle Window Examples

| machine_id   | start_time          | end_time            |   window_length | idle_type             |
|:-------------|:--------------------|:--------------------|----------------:|:----------------------|
| M-231        | 2026-01-01 01:01:40 | 2026-01-23 18:01:50 |          107209 | constant_low_variance |
| M-231        | 2026-02-14 05:09:30 | 2026-02-14 05:44:50 |             144 | frozen                |
| M-231        | 2026-02-16 08:29:37 | 2026-02-16 11:44:37 |             774 | frozen                |
| M-231        | 2026-02-16 11:58:57 | 2026-02-16 12:20:17 |              90 | frozen                |
| M-231        | 2026-02-16 13:51:09 | 2026-02-17 01:00:29 |            2069 | frozen                |
| M-356        | 2026-01-01 01:01:41 | 2026-01-03 15:46:21 |           12124 | constant_low_variance |
| M-356        | 2026-01-06 10:46:41 | 2026-01-06 18:42:01 |            1561 | frozen                |
| M-356        | 2026-01-06 18:48:11 | 2026-01-06 20:44:11 |             377 | frozen                |
| M-356        | 2026-01-06 20:54:41 | 2026-01-07 11:49:11 |            2928 | frozen                |
| M-356        | 2026-01-09 18:46:11 | 2026-01-09 19:57:41 |             237 | frozen                |
| M-356        | 2026-01-14 13:45:51 | 2026-01-14 14:52:41 |             217 | frozen                |
| M-356        | 2026-01-15 23:31:51 | 2026-01-16 09:15:21 |            1932 | frozen                |
| M-356        | 2026-01-16 13:26:51 | 2026-01-16 13:37:21 |              32 | frozen                |
| M-356        | 2026-01-16 16:15:21 | 2026-01-16 16:27:51 |              45 | frozen                |
| M-356        | 2026-01-22 05:34:01 | 2026-01-22 06:34:21 |             204 | frozen                |
| M-356        | 2026-01-22 07:21:11 | 2026-01-23 05:45:51 |            4408 | frozen                |
| M-356        | 2026-01-23 19:26:51 | 2026-01-23 23:45:01 |             851 | frozen                |
| M-356        | 2026-01-25 12:46:21 | 2026-01-25 12:56:21 |              32 | frozen                |
| M-356        | 2026-01-25 13:07:41 | 2026-01-26 17:31:21 |            5707 | frozen                |
| M-356        | 2026-01-28 19:49:11 | 2026-01-28 22:20:31 |             492 | frozen                |

## Idle vs Active Variability Comparison

| sensor                 |   idle_window_std_median |   active_window_std_median |   idle_window_std_mean |   active_window_std_mean |
|:-----------------------|-------------------------:|---------------------------:|-----------------------:|-------------------------:|
| cycle                  |              1.77636e-15 |                  0.774984  |             0.00446717 |                 1.38881  |
| injection_pressure     |              0           |                 24.739     |             0.00721813 |                32.5251   |
| switch_pressure        |              0           |                 24.6703    |             0.00636894 |                31.8692   |
| peak_pressure_position |              8.88178e-16 |                  0.0300842 |             0.0127888  |                 0.164271 |

## HYDRA Coverage

- HYDRA timestamp range: 2025-09-30 00:00:00 to 2026-02-15 00:00:00
- Idle windows with HYDRA overlap: 33/140
