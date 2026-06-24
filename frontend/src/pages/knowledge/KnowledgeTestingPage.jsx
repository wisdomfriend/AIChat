/**
 * 知识检索测试页 — 左右分栏布局。
 */
import { useState } from "react";
import { useParams } from "react-router-dom";
import {
  Button,
  Card,
  Input,
  Slider,
  Tag,
  Typography,
  message,
} from "antd";
import { FileSearchOutlined, SendOutlined } from "@ant-design/icons";
import { searchKnowledgeBase } from "../../api/knowledge";

const { TextArea } = Input;

export default function KnowledgeTestingPage() {
  const { kbId } = useParams();
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.2);
  const [vectorWeight, setVectorWeight] = useState(0.3);
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);

  async function handleSearch() {
    if (!query.trim()) {
      message.warning("请输入检索问题");
      return;
    }
    setSearching(true);
    try {
      const data = await searchKnowledgeBase(kbId, query.trim(), topK);
      let results = data.results || [];
      if (similarityThreshold > 0) {
        results = results.filter((item) => {
          const score = item.rerank_score ?? item.fusion_score ?? 0;
          return score >= similarityThreshold;
        });
      }
      setSearchResults(results);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "检索失败");
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="kb-detail-content">
      <Card className="gov-page-card" bordered={false}>
        <h1 className="kb-page-title">知识检索测试</h1>
        <p className="kb-page-desc">
          请完成召回测试，确保配置正确。此处修改不会自动保存，如需调整检索策略请修改服务端配置。
        </p>
      </Card>

      <Card className="gov-page-card" bordered={false} bodyStyle={{ padding: 0 }}>
        <div className="kb-testing-layout">
          <div className="kb-testing-left">
            <div className="kb-testing-section-title">测试设置</div>
            <div className="kb-testing-settings">
              <div className="kb-slider-row">
                <div className="kb-slider-label">
                  <span>相似度阈值</span>
                  <span className="kb-slider-value">{similarityThreshold.toFixed(2)}</span>
                </div>
                <Slider
                  min={0}
                  max={1}
                  step={0.05}
                  value={similarityThreshold}
                  onChange={setSimilarityThreshold}
                  tooltip={{ formatter: (v) => v?.toFixed(2) }}
                />
              </div>

              <div className="kb-slider-row">
                <div className="kb-slider-label">
                  <span>向量相似度权重</span>
                  <span className="kb-slider-value">
                    {vectorWeight.toFixed(2)} / {(1 - vectorWeight).toFixed(2)}
                  </span>
                </div>
                <Slider
                  min={0}
                  max={1}
                  step={0.05}
                  value={vectorWeight}
                  onChange={setVectorWeight}
                  tooltip={{ formatter: (v) => `向量 ${v?.toFixed(2)}` }}
                />
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  向量 {vectorWeight.toFixed(2)} · 全文 {(1 - vectorWeight).toFixed(2)}
                </Typography.Text>
              </div>

              <div className="kb-slider-row">
                <div className="kb-slider-label">
                  <span>返回条数 Top K</span>
                  <span className="kb-slider-value">{topK}</span>
                </div>
                <Slider min={1} max={20} step={1} value={topK} onChange={setTopK} />
              </div>
            </div>

            <div className="kb-testing-query">
              <TextArea
                rows={5}
                placeholder="请输入测试问题..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>

            <div className="kb-testing-actions">
              <Button
                type="primary"
                icon={<SendOutlined />}
                loading={searching}
                onClick={handleSearch}
                disabled={!query.trim()}
              >
                运行
              </Button>
            </div>
          </div>

          <div className="kb-testing-right">
            <div className="kb-testing-result-header">
              <div className="kb-testing-section-title" style={{ marginBottom: 0 }}>
                测试结果
              </div>
              {searchResults.length > 0 && (
                <Tag color="blue">{searchResults.length} 条命中</Tag>
              )}
            </div>

            {searchResults.length === 0 ? (
              <div className="kb-testing-empty">
                <FileSearchOutlined className="kb-testing-empty-icon" />
                <div>尚未运行测试，结果会显示在这里</div>
              </div>
            ) : (
              searchResults.map((item, index) => (
                <div key={`${item.document_id}-${item.chunk_index}-${index}`} className="kb-result-card">
                  <div className="kb-result-scores">
                    <Tag>{item.filename || "未知文档"}</Tag>
                    <Tag color="blue">片段 #{Number(item.chunk_index || 0) + 1}</Tag>
                    {item.vector_score != null && (
                      <Tag color="geekblue">向量 {item.vector_score.toFixed(3)}</Tag>
                    )}
                    {item.bm25_score != null && (
                      <Tag color="orange">BM25 {item.bm25_score.toFixed(3)}</Tag>
                    )}
                    {item.fusion_score != null && (
                      <Tag color="purple">融合 {item.fusion_score.toFixed(3)}</Tag>
                    )}
                    {item.rerank_score != null && (
                      <Tag color="green">Rerank {item.rerank_score.toFixed(3)}</Tag>
                    )}
                  </div>
                  <p className="kb-result-content">{item.content}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
