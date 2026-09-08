#version 330 core

out vec4 FragColor;

in vec3 ourColor;
in vec2 TexCoords;
in vec3 normal;
in vec3 fragPos;

struct Material{

	//vec3 ambient;
	//vec3 diffuse;
	//vec3 specular;
	float shininess;

	sampler2D diffuse;
	sampler2D specular;
};

struct DirLight{
	vec3 direction;

	vec3 ambient;
	vec3 diffuse;
	vec3 specular;
};

struct PointLight{
	vec3 position;

	float quadratic;
	float liner;
	float constant;

	vec3 ambient;
	vec3 diffuse;
	vec3 specular;
};

uniform Material mPink,mT1;
//uniform Light lWhite;
uniform DirLight lDir;
uniform PointLight lPoint[4];

uniform vec3 viewPos;

vec3 CalDirLight(DirLight light,vec3 norm,vec3 viewDir);
vec3 CalPointLight(PointLight light,vec3 norm,vec3 fragPosition,vec3 viewDir);

void main()
{
	//FragColor=vec4(xColor*ourColor.x,ourColor.y,ourColor.z,1.0f);
	//FragColor=texture(WaterTex,TexCoords);
	//FragColor=texture(WaterTex,TexCoords)*vec4(xColor*ourColor.x,ourColor.y,ourColor.z,1.0f);
	//FragColor=mix(texture(WaterTex,TexCoords),texture(BottleTex,TexCoords),0.1)*vec4(ourColor,1.0f);

	
	vec3 norm=normalize(normal);
	vec3 viewDir=normalize(viewPos-fragPos);

	vec3 result =CalDirLight(lDir,norm,viewDir);
	for(int i = 0 ;i < 4; i++)
		result+=CalPointLight(lPoint[i],norm,fragPos,viewDir);

	FragColor=vec4(result,1.0f);

}

vec3 CalDirLight(DirLight light,vec3 norm,vec3 viewDir){
	//光线
	vec3 lightDir=normalize(-light.direction);
	//漫反射
	float diff=max(dot(norm,lightDir),0.0f);
	//镜面反射
	vec3 reflectDir=reflect(-lightDir,norm);
	float spec=pow(max(dot(viewDir,reflectDir),0.0f),mT1.shininess);
	//光线计算
	vec3 ambient=light.ambient * texture(mT1.diffuse,TexCoords).rgb;
	vec3 diffuse =light.diffuse * diff * texture(mT1.diffuse,TexCoords).rgb;
	vec3 specular=light.specular * spec * texture(mT1.specular,TexCoords).rgb;

	return ambient + diffuse + specular;
}

vec3 CalPointLight(PointLight light,vec3 norm,vec3 fragPosition,vec3 viewDir){
	
	vec3 lightDir=normalize(light.position-fragPosition);
	
	float diff=max(dot(norm,lightDir),0.0f);
	
	vec3 reflectDir=reflect(-lightDir,norm);
	float spec=pow(max(dot(viewDir,reflectDir),0.0f),mT1.shininess);
	
	float Distance=length(light.position-fragPosition);
	float attenuation=1.0f/(light.constant+light.liner*Distance+light.quadratic*pow(Distance,2));

	vec3 ambient=light.ambient * texture(mT1.diffuse,TexCoords).rgb;
	vec3 diffuse =light.diffuse * diff * texture(mT1.diffuse,TexCoords).rgb;
	vec3 specular=light.specular * spec * texture(mT1.specular,TexCoords).rgb;

	ambient *= attenuation;
	diffuse *= attenuation;
	specular *= attenuation;

	return ambient + diffuse + specular;
}