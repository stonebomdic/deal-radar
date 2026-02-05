"""Scheduler module for periodic crawling and notification tasks.

Schedule overview:
  - 02:00 daily  - Promotion crawl
  - 04:00 daily  - Cleanup expired promotions
  - 06:00 daily  - Notify new promotions (after crawl)
  - 09:00 daily  - Notify expiring promotions
  - 03:00 Sunday - Card info crawl (includes new card notifications)
"""
