# SurfScout — Dad-friendly shell aliases
#
# Source this to try them in your current shell:
#   source ~/charos/surfscout/scripts/aliases.sh
#
# If you like them, add the source line to ~/.bashrc to make permanent.
# (Or copy the alias lines below directly into ~/.bashrc.)

# scout-warm — start a HEADED daemon so you can manually click through WAF
# challenges (Zillow's "Press & Hold", Akamai bot checks, etc.) and let
# cookies + fingerprint persist in the profile. After warming, use
# scout-read-warm <url> to read through the warmed session.
alias scout-warm='surfscout session start'

# scout-up — start a HEADLESS daemon for general scripted work.
alias scout-up='surfscout session start --headless'

# scout-down — stop the daemon cleanly. Always run when done.
alias scout-down='surfscout session stop'

# scout-status — quick "is the daemon alive, what's it doing" check.
alias scout-status='surfscout session status'

# scout-list — read a search-results / category page and DON'T let
# Readability gut the card grid. Use this instead of plain `surfscout read`
# whenever you're scraping a "list of items" page (LandWatch category,
# search results, paginated indexes, etc.).
alias scout-list='surfscout read --no-readability'

# scout-read-warm — read a URL through the warmed daemon profile (cookies,
# logged-in state, post-WAF-challenge fingerprint). Daemon must be running
# (use scout-warm first).
alias scout-read-warm='surfscout read --use-daemon'
