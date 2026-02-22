<form role="search" method="get" class="search-form" action="<?php echo esc_url(home_url('/')); ?>">
  <label>
    <span class="screen-reader-text"><?php echo esc_html_x('Search for:', 'label', 'ott-trendy-lite'); ?></span>
    <input type="search" class="search-field" placeholder="작품/배우/키워드 검색" value="<?php echo get_search_query(); ?>" name="s" />
  </label>
  <button type="submit" class="search-submit">검색</button>
</form>
