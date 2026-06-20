/**
 * 背景图候选预览（开发选型用）。
 * 访问 /bg-preview 查看全部候选图。
 */
import { Card, Col, Divider, Row, Tag, Typography } from "antd";
import "../styles/bg-preview.css";

const { Title, Paragraph, Text } = Typography;

const LIGHT_OPTIONS = [
  { id: "01", file: "bg-01.jpg", name: "柔和流线", desc: "白色流线 + 浅灰底，简洁政务风" },
  { id: "02", file: "bg-02.jpg", name: "淡彩抽象", desc: "淡彩色块，偏现代感" },
  { id: "03", file: "bg-03.jpg", name: "蓝白波浪", desc: "浅蓝渐变波纹，清爽专业" },
  { id: "04", file: "bg-04.jpg", name: "浅蓝曲线", desc: "玻璃质感曲线，科技感" },
  { id: "05", file: "bg-05.jpg", name: "渐变网格", desc: "蓝紫渐变，视觉层次丰富" },
  { id: "06", file: "bg-06.jpg", name: "彩虹渐变", desc: "多色柔和渐变，活泼一些" },
  { id: "07", file: "bg-07.jpg", name: "几何光斑", desc: "抽象几何 + 光晕，偏设计风" },
  { id: "08", file: "bg-08.jpg", name: "雪山云海", desc: "自然风景，大气沉稳" },
  { id: "09", file: "bg-09.jpg", name: "晨雾山水", desc: "雾气山峦，意境型背景" },
];

const AI_BLUE_OPTIONS = [
  { id: "10", file: "bg-10.jpg", name: "数字蓝墙", desc: "蓝黑数字纹理，经典科技风" },
  { id: "11", file: "bg-11.jpg", name: "蓝色光轨", desc: "深色底 + 蓝色光线，AI 感强" },
  { id: "12", file: "bg-12.jpg", name: "几何矩阵", desc: "蓝白几何图案，规整专业" },
  { id: "13", file: "bg-13.jpg", name: "数据线条", desc: "密集蓝白线条，信息流风格" },
  { id: "14", file: "bg-14.jpg", name: "能量隧道", desc: "蓝色能量通道 + 方块，未来感" },
  { id: "15", file: "bg-15.jpg", name: "电路芯片", desc: "电路板特写，硬核 AI 科技" },
  { id: "16", file: "bg-16.jpg", name: "深蓝网格", desc: "竖线网格，数据中心风格" },
  { id: "17", file: "bg-17.jpg", name: "AI 波纹", desc: "蓝粉流动波纹，智能助手气质" },
  { id: "18", file: "bg-18.jpg", name: "蓝色散景", desc: "蓝白光斑，柔和科技背景" },
];

function BgOptionGrid({ options, tagColor = "blue" }) {
  return (
    <Row gutter={[16, 16]}>
      {options.map((item) => (
        <Col xs={24} sm={12} lg={8} key={item.id}>
          <Card
            className="bg-preview-card"
            cover={
              <div
                className="bg-preview-cover"
                style={{
                  backgroundImage: `var(--app-bg-overlay), url(/images/bg-options/${item.file})`,
                }}
              >
                <Tag color={tagColor} className="bg-preview-tag">
                  {item.id}
                </Tag>
              </div>
            }
          >
            <Card.Meta title={`${item.id} · ${item.name}`} description={item.desc} />
          </Card>
        </Col>
      ))}
    </Row>
  );
}

export default function BgPreview() {
  return (
    <div className="bg-preview-page">
      <div className="bg-preview-header">
        <Title level={2}>背景图候选（18 张）</Title>
        <Paragraph type="secondary">
          以下为 Unsplash 免费可商用背景。请记下编号（如 <Text code>03</Text> 或 <Text code>14</Text>
          ），告诉我你的选择即可。
        </Paragraph>
      </div>

      <Title level={4} className="bg-preview-section-title">
        浅色系列（01 - 09）
      </Title>
      <BgOptionGrid options={LIGHT_OPTIONS} tagColor="blue" />

      <Divider />

      <Title level={4} className="bg-preview-section-title">
        AI 蓝色系列（10 - 18）
      </Title>
      <BgOptionGrid options={AI_BLUE_OPTIONS} tagColor="geekblue" />
    </div>
  );
}
