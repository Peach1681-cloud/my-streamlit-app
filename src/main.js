import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { STLExporter } from 'three/examples/jsm/exporters/STLExporter.js';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';

// 1. Scene
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xf0f0f0);

// 2. Camera
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.set(0, 0, 4);

// 3. Renderer
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// 4. Controls
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

// 5. Lights
const light = new THREE.DirectionalLight(0xffffff, 2.5);
light.position.set(2, 4, 5);
scene.add(light);

const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
scene.add(ambientLight);

const textureLoader = new THREE.TextureLoader();
const stlExporter = new STLExporter();
const objExporter = new OBJExporter();

function assignUVs(geometry) {
  geometry.computeBoundingBox();
  const max = geometry.boundingBox.max;
  const min = geometry.boundingBox.min;
  const offset = new THREE.Vector2(0 - min.x, 0 - min.y);
  const range = new THREE.Vector2(max.x - min.x, max.y - min.y);
  const pos = geometry.attributes.position;
  const uvs = [];

  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const u = (x + offset.x) / range.x;
    const v = (y + offset.y) / range.y;
    uvs.push(u, v);
  }
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
}

function createHeartGeometry() {
  const heartShape = new THREE.Shape();
  const x = 0, y = 0;
  
  heartShape.moveTo(x + 0.25, y + 0.25);
  heartShape.bezierCurveTo(x + 0.25, y + 0.25, x + 0.2, y, x, y);
  heartShape.bezierCurveTo(x - 0.3, y, x - 0.3, y + 0.35, x - 0.3, y + 0.35);
  heartShape.bezierCurveTo(x - 0.3, y + 0.55, x - 0.1, y + 0.77, x + 0.25, y + 0.95);
  heartShape.bezierCurveTo(x + 0.6, y + 0.77, x + 0.8, y + 0.55, x + 0.8, y + 0.35);
  heartShape.bezierCurveTo(x + 0.8, y + 0.35, x + 0.8, y, x + 0.5, y);
  heartShape.bezierCurveTo(x + 0.35, y, x + 0.25, y + 0.25, x + 0.25, y + 0.25);

  const extrudeSettings = {
    depth: 0.3, bevelEnabled: true, bevelSegments: 5,
    steps: 2, bevelSize: 0.08, bevelThickness: 0.08
  };

  const geo = new THREE.ExtrudeGeometry(heartShape, extrudeSettings);
  geo.center();
  assignUVs(geo);
  return geo;
}

let currentMaterial = new THREE.MeshStandardMaterial({ color: 0xe74c3c, roughness: 0.3 });
let currentMesh = new THREE.Mesh(createHeartGeometry(), currentMaterial);
scene.add(currentMesh);

document.getElementById('heartBtn').addEventListener('click', () => {
  currentMesh.geometry.dispose();
  currentMesh.geometry = createHeartGeometry();
});

document.getElementById('cubeBtn').addEventListener('click', () => {
  currentMesh.geometry.dispose();
  const boxGeo = new THREE.BoxGeometry(1.8, 1.8, 1.8);
  assignUVs(boxGeo);
  currentMesh.geometry = boxGeo;
});

document.getElementById('changeColorBtn').addEventListener('click', () => {
  currentMesh.material.map = null;
  currentMesh.material.needsUpdate = true;
  currentMesh.material.color.setHex(Math.random() * 0xffffff);
});

const imageUpload = document.getElementById('imageUpload');
imageUpload.addEventListener('change', (event) => {
  const file = event.target.files[0];
  if (file) {
    const reader = new FileReader();
    reader.onload = function (e) {
      textureLoader.load(e.target.result, (texture) => {
        texture.colorSpace = THREE.SRGBColorSpace;
        currentMesh.material.color.setHex(0xffffff);
        currentMesh.material.map = texture;
        currentMesh.material.needsUpdate = true;
      });
    };
    reader.readAsDataURL(file);
  }
});

// Export System (STL / OBJ)
const exportBtn = document.getElementById('exportBtn');
exportBtn.addEventListener('click', () => {
  const selectedFormat = document.getElementById('exportFormat').value;

  if (selectedFormat === 'stl') {
    const result = stlExporter.parse(currentMesh);
    saveString(result, 'my-model.stl');
  } else if (selectedFormat === 'obj') {
    const result = objExporter.parse(currentMesh);
    saveString(result, 'my-model.obj');
  }
});

function saveString(text, filename) {
  save(new Blob([text], { type: 'text/plain' }), filename);
}

function save(blob, filename) {
  const link = document.createElement('a');
  link.style.display = 'none';
  document.body.appendChild(link);
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(link.href);
}

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}

animate();