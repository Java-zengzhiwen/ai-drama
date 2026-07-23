import { SearchOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Input, Typography } from "antd";
import { useMemo, useState } from "react";
import { Link, useInRouterContext } from "react-router-dom";
import { listChapters, type ChapterRead } from "../projects/api";

type ChapterNavigatorProps = {
  chapter: ChapterRead;
  currentStateLabel?: string;
};

export function ChapterNavigator({ chapter, currentStateLabel }: ChapterNavigatorProps) {
  const inRouterContext = useInRouterContext();
  const [chapterSearch, setChapterSearch] = useState("");
  const chaptersQuery = useQuery({
    queryKey: ["chapters", chapter.project_id],
    queryFn: () => listChapters(chapter.project_id),
  });
  const filteredChapters = useMemo(() => {
    const chapters = chaptersQuery.data ?? [chapter];
    const query = chapterSearch.trim().toLowerCase();
    return chapters
      .filter((item) => !query || item.title.toLowerCase().includes(query))
      .sort((left, right) => left.position - right.position);
  }, [chapter, chapterSearch, chaptersQuery.data]);

  return (
    <nav aria-label="章节导航" className="source-chapter-nav">
      <div className="source-panel-heading">
        <strong>章节导航</strong>
        <span>{filteredChapters.length} 章</span>
      </div>
      <Input
        allowClear
        aria-label="搜索章节标题"
        onChange={(event) => setChapterSearch(event.target.value)}
        placeholder="搜索章节标题"
        prefix={<SearchOutlined />}
        value={chapterSearch}
      />
      <div className="source-chapter-list">
        {filteredChapters.map((item) => {
          const current = item.chapter_id === chapter.chapter_id;
          const complete = Boolean(item.current_source_revision_id);
          const stateLabel = current && currentStateLabel
            ? currentStateLabel
            : complete
              ? "原文已确认"
              : current
                ? "原文处理中"
                : "未开始";
          const chapterLinkContent = (
            <>
              <span className="source-chapter-position">{String(item.position).padStart(2, "0")}</span>
              <span className="source-chapter-title">{item.title}</span>
              <span className="source-chapter-state" data-complete={complete}>
                <i aria-hidden="true" />
                {stateLabel}
              </span>
            </>
          );
          const href = `/projects/${item.project_id}/chapters/${item.chapter_id}`;
          return inRouterContext ? (
            <Link
              aria-current={current ? "page" : undefined}
              className="source-chapter-link"
              data-current={current}
              key={item.chapter_id}
              to={href}
            >
              {chapterLinkContent}
            </Link>
          ) : (
            <a
              aria-current={current ? "page" : undefined}
              className="source-chapter-link"
              data-current={current}
              href={href}
              key={item.chapter_id}
            >
              {chapterLinkContent}
            </a>
          );
        })}
        {!filteredChapters.length ? (
          <Typography.Text className="source-chapter-empty" type="secondary">
            没有匹配章节
          </Typography.Text>
        ) : null}
      </div>
      {inRouterContext ? (
        <Link className="source-new-chapter" to={`/projects/${chapter.project_id}`}>
          ＋ 新建章节
        </Link>
      ) : (
        <a className="source-new-chapter" href={`/projects/${chapter.project_id}`}>
          ＋ 新建章节
        </a>
      )}
    </nav>
  );
}
