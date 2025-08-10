# Gatherer Comment Section Archive (version 1.1)

## ChangeLog:

- 1.1 (2025/07/29): Added identifiers to the data set.
- 1.0 (2025/07/28): First release.

## Description

This data set contains what should be the complete content of the comment
section that was available on the Gatherer website until its removal in June
2025. It is provided as is for archival purposes. This data was not collected
by scraping the webpages. Instead, it was extracted by querying the following
endpoint directly: `http://gatherer.wizards.com/Handlers/RPCUtilities.ashx`

When sent the correct payload, this server would return all the data for a
given card comment. As a result, this data set contains information that was
typically not shown to users like the original (i.e. unredacted) version of
each comment. The JSON data returned by the server contained a lot of empty
or redundant values. To save on storage space, that information has been
ommitted.

## Data Organization:

The data is provided as a set of JSON files. Each one stores the comments
for all cards in a given set identified by its three-letter code and its
(approximative) release date. Comments posted by users are keyed by the card
they apply to and sorted chronologically based on the "timestamp" field. The
excerpt below describes the content of an entry:

```json
[
  "<multiverse id>: <card name>": [
    {
      "author": "<Username of the post's author>",
      "author_id": "<Unique identifier of the post's author>",
      "datetime": "<Post creation date in YYYY-MM-DD hh:mm:ss format>",
      "id": "<Unique identifier of the post>",
      "text_parsed": "<Text as displayed by Gatherer>",
      "text_posted": "<Text as posted by the author>",
      "timestamp": "<Post creation timestamp>",
      "vote_count": <Number of votes for the post>,
      "vote_sum": <Total sum of the votes for the post>
    },
    ...
  ],
  ...
]
```

## Notes:

The content of the "text_posted" field is the raw version of the comment
as posted by the user, including swear words. It may also contain special
directives (e.g. `[b]`, `[i]`, or `[autocard]`) which are converted into
HTML tags for display purposes.

The content of the `text_parsed` field is the version of the comment as
shown to other users. Swear words are typically replaced with `*` characters,
directives and newline characters are replaced with their corresponding HTML
tags, and special characters are escaped.

Each vote assigns a score from 1 to 10 to the post. Gatherer used to display
ratings out of 5 stars instead of 10. As a result, the rating of a given post
is given by the formula: `vote_sum / (2 * vote_count)`.

The `timestamp` field is somewhat redundant with the `datetime` one. It is
nonetheless useful to infer the time zone associated with the dates and times
since none is available.
