from adapters.richland_library.parser import clean_title, parse_event_anchor, parse_event_block


def test_event_anchor_excludes_popover_metadata_from_title() -> None:
    block = '''
    <div class="s-lc-mc-evt">
      <a href="https://myrichlandlibrary.libcal.com/event/16647056"
         data-content="&lt;dl&gt;&lt;dt&gt;From&lt;/dt&gt;&lt;dd&gt;1:00 PM Sunday, July 12th, 2026&lt;/dd&gt;&lt;dt&gt;Audience&lt;/dt&gt;&lt;dd&gt;Adult&lt;/dd&gt;&lt;dt&gt;Description&lt;/dt&gt;&lt;dd&gt;Just in time for Shark Week.&lt;/dd&gt;&lt;/dl&gt;">
        Shark Week Movie: Jaws
      </a>
      <div class="s-lc-mc-evt-time">1:00 PM</div>
      <div class="s-lc-mc-evt-loc">Richland Library</div>
    </div></div>
    '''

    assert parse_event_anchor(block) == (
        "https://myrichlandlibrary.libcal.com/event/16647056",
        "Shark Week Movie: Jaws",
    )


def test_event_block_keeps_description_separate_from_title() -> None:
    block = '''
    <div class="s-lc-mc-evt">
      <a href="https://myrichlandlibrary.libcal.com/event/16647056"
         data-content="&lt;dl&gt;&lt;dt&gt;From&lt;/dt&gt;&lt;dd&gt;1:00 PM Sunday, July 12th, 2026&lt;/dd&gt;&lt;dt&gt;To&lt;/dt&gt;&lt;dd&gt;3:30 PM Sunday, July 12th, 2026&lt;/dd&gt;&lt;dt&gt;Audience&lt;/dt&gt;&lt;dd&gt;Adult&lt;/dd&gt;&lt;dt&gt;Description&lt;/dt&gt;&lt;dd&gt;Just in time for Shark Week.&lt;/dd&gt;&lt;/dl&gt;">
        Shark Week Movie: Jaws
      </a>
      <div class="s-lc-mc-evt-time">1:00 PM</div>
      <div class="s-lc-mc-evt-loc">Richland Library</div>
    </div></div>
    '''

    event = parse_event_block(block)

    assert event is not None
    assert event["title"] == "Shark Week Movie: Jaws"
    assert event["description"] == "Just in time for Shark Week."
    assert event["start_date"] == "2026-07-12"
    assert event["start_time"] == "13:00"
    assert event["end_time"] == "15:30"


def test_clean_title_removes_adjacent_duplicate_accessibility_prefix() -> None:
    assert clean_title(
        "Family Movies ofFamily Movies of the 1990s: Jumanji, The Sandlot, and Matilda"
    ) == "Family Movies of the 1990s: Jumanji, The Sandlot, and Matilda"


def test_event_anchor_ignores_non_event_links() -> None:
    assert parse_event_anchor('<a href="tel:509-783-7878">(509) 783-7878</a>') is None
