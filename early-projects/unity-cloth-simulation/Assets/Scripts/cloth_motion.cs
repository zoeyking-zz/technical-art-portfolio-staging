using UnityEngine;
using System.Collections;

public class cloth_motion : MonoBehaviour
{

    float t;
    int[] edge_list;
    float mass;
    float damping;
    float stiffness;
    float[] L0;
    Vector3[] velocities;
    float w;
    Vector3 g = new Vector3(0.0f, -0.5f, 0.0f);
    Mesh mesh;
    Vector3[] vertices;
    public GameObject ball;
    
    void Start()
    {
        t = 0.075f;
        mass = 1.0f;
        w = 0.2f;
        damping = 0.9f;
        stiffness = 1000.0f;
        mesh = GetComponent<MeshFilter>().mesh;
        int[] triangles = mesh.triangles;
        vertices = mesh.vertices;
        ball = GameObject.Find("Sphere");
        
        int[] original_edge_list = new int[triangles.Length * 2];
        for (int i = 0; i < triangles.Length; i += 3)
        {
            original_edge_list[i * 2 + 0] = triangles[i + 0];
            original_edge_list[i * 2 + 1] = triangles[i + 1];
            original_edge_list[i * 2 + 2] = triangles[i + 1];
            original_edge_list[i * 2 + 3] = triangles[i + 2];
            original_edge_list[i * 2 + 4] = triangles[i + 2];
            original_edge_list[i * 2 + 5] = triangles[i + 0];
        }
        
        for (int i = 0; i < original_edge_list.Length; i += 2)
            if (original_edge_list[i] > original_edge_list[i + 1])
                Swap(ref original_edge_list[i], ref original_edge_list[i + 1]);
        
        Quick_Sort(ref original_edge_list, 0, original_edge_list.Length / 2 - 1);
        int count = 0;
        for (int i = 0; i < original_edge_list.Length; i += 2)
            if (i == 0 ||
                original_edge_list[i + 0] != original_edge_list[i - 2] ||
                original_edge_list[i + 1] != original_edge_list[i - 1])
                count++;

        edge_list = new int[count * 2];
        int r_count = 0;
        for (int i = 0; i < original_edge_list.Length; i += 2)
            if (i == 0 ||
                original_edge_list[i + 0] != original_edge_list[i - 2] ||
                original_edge_list[i + 1] != original_edge_list[i - 1])
            {
                edge_list[r_count * 2 + 0] = original_edge_list[i + 0];
                edge_list[r_count * 2 + 1] = original_edge_list[i + 1];
                r_count++;
            }
        
        L0 = new float[edge_list.Length / 2];
        for (int e = 0; e < edge_list.Length / 2; e++)
        {
            int v0 = edge_list[e * 2 + 0];
            int v1 = edge_list[e * 2 + 1];
            L0[e] = (vertices[v0] - vertices[v1]).magnitude;
        }
        
        velocities = new Vector3[vertices.Length];
        for (int v = 0; v < vertices.Length; v++)
            velocities[v] = new Vector3(0, 0, 0);
        
    }
    void Quick_Sort(ref int[] a, int l, int r)
    {
        int j;
        if (l < r)
        {
            j = Quick_Sort_Partition(ref a, l, r);
            Quick_Sort(ref a, l, j - 1);
            Quick_Sort(ref a, j + 1, r);
        }
    }
    int Quick_Sort_Partition(ref int[] a, int l, int r)
    {
        int pivot_0, pivot_1, i, j;
        pivot_0 = a[l * 2 + 0];
        pivot_1 = a[l * 2 + 1];
        i = l;
        j = r + 1;
        while (true)
        {
            do ++i; while (i <= r && (a[i * 2] < pivot_0 || a[i * 2] == pivot_0 && a[i * 2 + 1] <= pivot_1));
            do --j; while (a[j * 2] > pivot_0 || a[j * 2] == pivot_0 && a[j * 2 + 1] > pivot_1);
            if (i >= j) break;
            Swap(ref a[i * 2], ref a[j * 2]);
            Swap(ref a[i * 2 + 1], ref a[j * 2 + 1]);
        }
        Swap(ref a[l * 2 + 0], ref a[j * 2 + 0]);
        Swap(ref a[l * 2 + 1], ref a[j * 2 + 1]);
        return j;
    }
    void Swap(ref int a, ref int b)
    {
        int temp = a;
        a = b;
        b = temp;
    }


    void Strain_Limiting()
    {
        Vector3[] sumV = new Vector3[vertices.Length];
        int[] count = new int[vertices.Length];
        for (int e = 0; e < edge_list.Length / 2; e++)
        {
            int v0 = edge_list[e * 2 + 0];
            int v1 = edge_list[e * 2 + 1];
            sumV[v0] += .5f * (vertices[v0] + vertices[v1]
                + L0[e] * ((vertices[v0] - vertices[v1]) / (vertices[v0] - vertices[v1]).magnitude));
            sumV[v1] += .5f * (vertices[v0] + vertices[v1]
                + L0[e] * ((vertices[v1] - vertices[v0]) / (vertices[v1] - vertices[v0]).magnitude));
            count[v0]++;
            count[v1]++;
        }
        for (int i = 0; i < vertices.Length; i++)
        {
            sumV[i] = (w * vertices[i] + sumV[i]) / (w + (float)count[i]);
            velocities[i] += (sumV[i] - vertices[i]) / Time.deltaTime;
        }
    }


    void Collision_Handling()
    {
        transform.TransformPoint(transform.localPosition);
        Vector3[] vertices2 = mesh.vertices;
        Vector3 c = ball.transform.position;
        //Vector3 c = ball.transform.TransformPoint(ball.transform.position);
        float R = ball.transform.localScale.x / 2;
       

        for (int i = 0; i < vertices.Length; i++)
        {
            if ((c - vertices[i]).magnitude <= R)
            {
                vertices2[i] = c + R * (vertices[i] - c) / (vertices[i] - c).magnitude;
                velocities[i] += (vertices2[i] - vertices[i]) / Time.deltaTime;
            }
        }
    }
    
    void Update()
    {
        Strain_Limiting();
        Collision_Handling();
        for (int i = 0; i < 121; i++)
        {
            velocities[i] *= damping;
            if (i != 0 && i != 10)
                velocities[i] += g;
        }
        velocities[0] = new Vector3(0f, 0f, 0f);
        velocities[10] = new Vector3(0f, 0f, 0f);
        for (int i=0; i < vertices.Length;i++)
            vertices[i] += Time.deltaTime * velocities[i];
        mesh.vertices = vertices;
        mesh.RecalculateNormals();
    }

}
