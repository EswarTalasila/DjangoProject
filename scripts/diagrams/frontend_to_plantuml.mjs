#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..', '..');

const args = parseArgs(process.argv.slice(2));
const outPath = args.out;
if (!outPath) {
  console.error('Missing --out');
  process.exit(1);
}

const roots = (args.roots || 'frontend/src/app,frontend/src/services')
  .split(',')
  .map((root) => root.trim())
  .filter(Boolean)
  .map((root) => path.resolve(repoRoot, root));

const require = createRequire(import.meta.url);
let ts;
try {
  ts = require('typescript');
} catch (err) {
  const typescriptPath = path.resolve(repoRoot, 'frontend', 'node_modules', 'typescript');
  ts = require(typescriptPath);
}

const files = new Set();
for (const root of roots) {
  collectFiles(root, files);
}

const classes = [];
const relations = new Set();
const packages = new Map();

for (const file of files) {
  const sourceText = fs.readFileSync(file, 'utf8');
  const sourceFile = ts.createSourceFile(file, sourceText, ts.ScriptTarget.Latest, true);
  const relDir = path.dirname(path.relative(repoRoot, file));
  const packageName = relDir.replace(/\\/g, '/');
  const parsed = parseSource(sourceFile, file);
  if (!parsed.items.length) {
    continue;
  }
  if (!packages.has(packageName)) {
    packages.set(packageName, []);
  }
  packages.get(packageName).push(...parsed.items);
  for (const relation of parsed.relations) {
    relations.add(relation);
  }
}

const lines = [
  '@startuml',
  'hide circle',
  'skinparam classAttributeIconSize 0',
  '',
];

for (const [pkg, items] of Array.from(packages.entries()).sort(([a], [b]) => a.localeCompare(b))) {
  lines.push(`package "${pkg}" {`);
  for (const item of items) {
    lines.push(...item);
  }
  lines.push('}');
  lines.push('');
}

for (const relation of Array.from(relations).sort()) {
  lines.push(relation);
}

lines.push('@enduml');
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, lines.join('\n') + '\n', 'utf8');
console.log(`Wrote ${outPath}`);

function parseSource(sourceFile, filePath) {
  const items = [];
  const relations = [];

  function visit(node) {
    if (ts.isClassDeclaration(node) && node.name) {
      const className = node.name.text;
      items.push(renderClass(node, sourceFile, className));
      relations.push(...renderHeritage(node, className));
    }
    if (ts.isInterfaceDeclaration(node) && node.name) {
      const name = node.name.text;
      items.push(renderInterface(node, sourceFile, name));
      relations.push(...renderHeritage(node, name));
    }
    ts.forEachChild(node, visit);
  }

  visit(sourceFile);
  return { items, relations };
}

function renderClass(node, sourceFile, name) {
  const lines = [`class ${name} {`];
  for (const member of node.members) {
    if (ts.isConstructorDeclaration(member)) {
      lines.push(`  ${visibility(member)}constructor(${formatParams(member.parameters, sourceFile)})`);
      continue;
    }
    if (ts.isMethodDeclaration(member) && member.name) {
      const methodName = member.name.getText(sourceFile);
      const params = formatParams(member.parameters, sourceFile);
      const returnType = member.type ? member.type.getText(sourceFile) : 'void';
      lines.push(`  ${visibility(member)}${methodName}(${params}): ${returnType}`);
      continue;
    }
    if (ts.isPropertyDeclaration(member) && member.name) {
      const propName = member.name.getText(sourceFile);
      const propType = member.type ? member.type.getText(sourceFile) : 'any';
      lines.push(`  ${visibility(member)}${propName}: ${propType}`);
    }
  }
  lines.push('}');
  return lines;
}

function renderInterface(node, sourceFile, name) {
  const lines = [`interface ${name} {`];
  for (const member of node.members) {
    if (ts.isMethodSignature(member) && member.name) {
      const methodName = member.name.getText(sourceFile);
      const params = formatParams(member.parameters, sourceFile);
      const returnType = member.type ? member.type.getText(sourceFile) : 'void';
      lines.push(`  +${methodName}(${params}): ${returnType}`);
      continue;
    }
    if (ts.isPropertySignature(member) && member.name) {
      const propName = member.name.getText(sourceFile);
      const propType = member.type ? member.type.getText(sourceFile) : 'any';
      lines.push(`  +${propName}: ${propType}`);
    }
  }
  lines.push('}');
  return lines;
}

function renderHeritage(node, name) {
  const lines = [];
  if (!node.heritageClauses) {
    return lines;
  }
  for (const clause of node.heritageClauses) {
    for (const type of clause.types) {
      const baseName = type.expression.getText();
      if (!baseName) {
        continue;
      }
      if (clause.token === ts.SyntaxKind.ExtendsKeyword) {
        lines.push(`${name} --|> ${baseName}`);
      } else if (clause.token === ts.SyntaxKind.ImplementsKeyword) {
        lines.push(`${name} ..|> ${baseName}`);
      }
    }
  }
  return lines;
}

function formatParams(params, sourceFile) {
  return params
    .map((param) => {
      const name = param.name.getText(sourceFile);
      const type = param.type ? param.type.getText(sourceFile) : 'any';
      return `${name}: ${type}`;
    })
    .join(', ');
}

function visibility(member) {
  if (!member.modifiers) {
    return '+';
  }
  for (const modifier of member.modifiers) {
    if (modifier.kind === ts.SyntaxKind.PrivateKeyword) {
      return '-';
    }
    if (modifier.kind === ts.SyntaxKind.ProtectedKeyword) {
      return '#';
    }
  }
  return '+';
}

function collectFiles(root, files) {
  if (!fs.existsSync(root)) {
    return;
  }
  const stats = fs.statSync(root);
  if (stats.isDirectory()) {
    for (const entry of fs.readdirSync(root)) {
      if (entry.startsWith('.')) {
        continue;
      }
      collectFiles(path.join(root, entry), files);
    }
    return;
  }
  if (!root.endsWith('.ts')) {
    return;
  }
  if (root.endsWith('.spec.ts')) {
    return;
  }
  files.add(root);
}

function parseArgs(argv) {
  const parsed = {};
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--out') {
      parsed.out = argv[i + 1];
      i += 1;
      continue;
    }
    if (arg === '--roots') {
      parsed.roots = argv[i + 1];
      i += 1;
    }
  }
  return parsed;
}
