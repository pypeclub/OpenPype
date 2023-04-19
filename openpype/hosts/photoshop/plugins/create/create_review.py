from openpype.hosts.photoshop.lib import PSAutoCreator


class ReviewCreator(PSAutoCreator):
    """Creates review instance which might be disabled from publishing."""
    identifier = "review"
    family = "review"

    default_variant = "Main"

    def get_detail_description(self):
        return """Auto creator for review.

        Photoshop review is created from all published images or from all
        visible layers if no `image` instances got created.
        
        Review might be disabled by an artist (instance shouldn't be deleted as
        it will get recreated in next publish either way).
        """