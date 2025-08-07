"""Tests for the Discord bot functionality."""

from src.discord_bot.bot import MIN_RATING_THRESHOLD, create_book_embed


class TestCreateBookEmbed:
    """Test cases for the create_book_embed function."""

    def test_create_book_embed_with_sufficient_ratings(self):
        """Test that rating is shown when there are enough ratings."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "rating": 4.5,
            "ratings_count": 10,  # Above MIN_RATING_THRESHOLD
            "pages": 200,
            "release_year": 2023,
        }

        embed = create_book_embed(book_data)

        # Check that the embed has the expected fields
        field_names = [field.name for field in embed.fields]
        field_values = [field.value for field in embed.fields]

        assert "Rating" in field_names
        rating_index = field_names.index("Rating")
        assert "⭐ 4.5" in field_values[rating_index]

    def test_create_book_embed_with_insufficient_ratings(self):
        """Test that rating is omitted when there are not enough ratings."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "rating": 4.5,
            "ratings_count": 3,  # Below MIN_RATING_THRESHOLD
            "pages": 200,
            "release_year": 2023,
        }

        embed = create_book_embed(book_data)

        # Check that rating is not displayed
        field_names = [field.name for field in embed.fields]
        assert "Rating" not in field_names

        # But other fields should still be there
        assert "Pages" in field_names
        assert "Year" in field_names

    def test_create_book_embed_with_exactly_threshold_ratings(self):
        """Test rating is shown when ratings_count equals MIN_RATING_THRESHOLD."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "rating": 4.2,
            "ratings_count": MIN_RATING_THRESHOLD,  # Exactly at threshold
            "pages": 150,
        }

        embed = create_book_embed(book_data)

        field_names = [field.name for field in embed.fields]
        field_values = [field.value for field in embed.fields]

        assert "Rating" in field_names
        rating_index = field_names.index("Rating")
        assert "⭐ 4.2" in field_values[rating_index]

    def test_create_book_embed_with_no_rating(self):
        """Test that no rating is shown when rating is None."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "rating": None,
            "ratings_count": 10,
            "pages": 200,
        }

        embed = create_book_embed(book_data)

        field_names = [field.name for field in embed.fields]
        assert "Rating" not in field_names

    def test_create_book_embed_with_no_ratings_count(self):
        """Test that no rating is shown when ratings_count is None."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "rating": 4.5,
            "ratings_count": None,
            "pages": 200,
        }

        embed = create_book_embed(book_data)

        field_names = [field.name for field in embed.fields]
        assert "Rating" not in field_names

    def test_create_book_embed_shows_readers_count_regardless(self):
        """Test that readers count is shown even when rating is omitted."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "rating": 4.5,
            "ratings_count": 3,  # Below threshold
            "pages": 200,
        }

        embed = create_book_embed(book_data)

        field_names = [field.name for field in embed.fields]
        field_values = [field.value for field in embed.fields]

        # Rating should not be shown
        assert "Rating" not in field_names

        # But readers count should be shown
        assert "Readers" in field_names
        readers_index = field_names.index("Readers")
        assert "3" in field_values[readers_index]

    def test_create_book_embed_with_zero_ratings_count(self):
        """Test that rating is not shown when ratings_count is 0."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "rating": 4.5,
            "ratings_count": 0,  # Zero ratings
            "pages": 200,
        }

        embed = create_book_embed(book_data)

        field_names = [field.name for field in embed.fields]
        assert "Rating" not in field_names
        # Readers field also shouldn't be shown when count is 0
        assert "Readers" not in field_names

    def test_create_book_embed_basic_fields_always_present(self):
        """Test that basic book information is always present."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "rating": 4.5,
            "ratings_count": 2,  # Below threshold
        }

        embed = create_book_embed(book_data)

        # Basic embed properties should always be set
        assert embed.title == "Test Book"
        assert "Test Author" in embed.description
        assert embed.color.value == 0xFFA227
        assert embed.footer.text == "Dungeon Books • Powered by Hardcover API"
